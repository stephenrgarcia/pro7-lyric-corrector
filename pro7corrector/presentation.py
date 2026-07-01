"""High-level orchestration: load a .pro presentation, correct its lyric RTF,
and verify that nothing but the intended lyric text changed.

Confirmed against the real library:
  * Lyric text is the RTF at protobuf path .../13/5 (field `find_rtf_leaves`).
  * ProPresenter renders from that RTF. The sibling plain-text field (field 2)
    is a vestigial template string ("There's nothing worth more...") that the
    app ignores for display, so we never touch it.

Preservation invariant (the core safety check): blank every RTF leaf to empty
in both the original and the corrected tree, serialize, and compare. If the two
are byte-identical, then *everything* except RTF leaves -- slide/cue count,
UUIDs, group names, arrangements, labels, notes, media cues, the plain-text
field, and every other byte -- is provably unchanged, and the RTF leaves occupy
the same positions. We then check that the only RTF leaves whose text changed
are the ones we intended, and each matches the deterministic correction.
"""

from __future__ import annotations
import copy

from . import wire, rtf, rules

# A correction whose length changes by more than this fraction AND more than
# this many characters is treated as suspicious and skipped (defensive).
_SUSPICIOUS_FRACTION = 0.4
_SUSPICIOUS_CHARS = 40


class SlideChange:
    __slots__ = ("index", "old_text", "new_text", "notes")

    def __init__(self, index, old_text, new_text, notes):
        self.index = index
        self.old_text = old_text
        self.new_text = new_text
        self.notes = notes


class FileResult:
    __slots__ = ("changed", "changes", "flags", "skipped_dirty",
                 "skipped_suspicious", "lyric_slides", "error", "new_bytes",
                 "title_change")

    def __init__(self):
        self.changed = False
        self.changes = []
        self.flags = []
        self.skipped_dirty = 0
        self.skipped_suspicious = 0
        self.lyric_slides = 0
        self.error = None
        self.new_bytes = None
        self.title_change = None       # (old_title, new_title) or None


def _find_title_node(tree):
    """The presentation name is top-level protobuf field 3.

    Returned regardless of how the schema-less parser classified it: a title
    string whose bytes coincidentally form valid wire format (e.g. "After You")
    can be parsed as a sub-message rather than a string. We match by field
    number so all downstream handling is classification-independent.
    """
    for node in tree:
        if node[1] == 3 and node[0] in ("b", "m"):
            return node
    return None


def _title_bytes(node):
    """Raw title bytes, whether the node was parsed as a string or a message."""
    if node is None:
        return None
    if node[0] == "b":
        return node[2]
    return wire.serialize(node[2])     # mis-classified string -> reconstruct


def _set_title(node, new_bytes):
    """Force the field-3 node to a plain string leaf carrying new_bytes."""
    node[:] = ["b", 3, new_bytes]


# Titles to leave alone if encountered as the *desired* value (defensive).
def _safe_title(s):
    return bool(s) and s.strip() != "" and "\n" not in s and len(s) < 200


def presentation_title(tree, path=None) -> str:
    node = _find_title_node(tree)
    if node is not None:
        try:
            t = _title_bytes(node).decode("utf-8")
            if t.strip():
                return t
        except (UnicodeDecodeError, AttributeError):
            pass
    if path:
        import os as _os
        return _os.path.splitext(_os.path.basename(path))[0]
    return "(unknown)"


def _blank_rtf_serialize(tree, blank_title=False) -> bytes:
    t = copy.deepcopy(tree)
    for _, node in wire.find_rtf_leaves(t):
        node[2] = b""
    if blank_title:
        tn = _find_title_node(t)
        if tn is not None:
            _set_title(tn, b"")        # canonical empty leaf, any original kind
    return wire.serialize(t)


def _suspicious(old: str, new: str) -> bool:
    delta = abs(len(new) - len(old))
    if delta <= _SUSPICIOUS_CHARS:
        return False
    base = max(len(old), 1)
    return delta / base > _SUSPICIOUS_FRACTION


def process_bytes(data: bytes, cfg: rules.Config = rules.DEFAULT,
                  desired_title=None) -> FileResult:
    """Return a FileResult; new_bytes is set only when a verified change exists.

    If `desired_title` is given (normally the filename stem), the presentation's
    internal title (field 3, what ProPresenter shows in its library) is set to
    it when it differs -- so titles read as clean Title Case, not 'Untitled' or
    a stale/typo'd name.
    """
    res = FileResult()
    try:
        tree = wire.parse(data)
    except wire.WireError as e:
        res.error = "parse failed: %s" % e
        return res

    # Plan a title fix (a non-lyric change, verified separately below).
    if desired_title is not None and cfg.fix_title and _safe_title(desired_title):
        tnode = _find_title_node(tree)
        if tnode is not None:
            try:
                cur = _title_bytes(tnode).decode("utf-8")
            except (UnicodeDecodeError, AttributeError):
                cur = None
            if cur is not None and cur != desired_title:
                res.title_change = (cur, desired_title)

    leaves = wire.find_rtf_leaves(tree)
    # Snapshot original RTF values (positional) for verification.
    original_values = [node[2] for _, node in leaves]
    intended = {}        # leaf index -> corrected display text (for verify)
    coded_edits = {}     # leaf index -> corrected coded text (for splice)

    for idx, (_, node) in enumerate(leaves):
        payload = node[2]
        parsed = rtf.extract(payload)
        if not parsed.text.strip():
            continue                       # empty box
        res.lyric_slides += 1
        if not parsed.clean:
            res.skipped_dirty += 1          # special glyph -> left as is
            continue
        cr = rules.correct_text(parsed.coded, cfg)
        for fl in cr.flags:
            if fl not in res.flags:
                res.flags.append(fl)
        if not cr.changed:
            continue
        old_display = parsed.text
        new_display = rtf.display(cr.text)
        if _suspicious(old_display, new_display):
            res.skipped_suspicious += 1
            continue
        # Confirm the corrected text still splices (segment structure intact).
        if rtf.splice(payload, cr.text, parsed) is None:
            res.skipped_suspicious += 1
            continue
        intended[idx] = new_display
        coded_edits[idx] = cr.text
        res.changes.append(SlideChange(idx, old_display, new_display, cr.notes))

    if not intended and not res.title_change:
        res.changed = False
        return res

    # Apply splices on a working copy of the tree.
    work = wire.parse(data)
    work_leaves = wire.find_rtf_leaves(work)
    for idx, coded in coded_edits.items():
        node = work_leaves[idx][1]
        parsed = rtf.extract(node[2])
        spliced = rtf.splice(node[2], coded, parsed)
        if spliced is None:
            res.error = "splice failed at leaf %d" % idx
            return res
        node[2] = spliced
    if res.title_change:
        _set_title(_find_title_node(work), res.title_change[1].encode("utf-8"))

    new_bytes = wire.serialize(work)

    ok, reason = _verify(data, new_bytes, original_values, intended,
                         res.title_change)
    if not ok:
        res.error = "verification failed: %s" % reason
        res.changed = False
        res.changes = []
        res.title_change = None
        return res

    res.new_bytes = new_bytes
    res.changed = True
    return res


def _verify(orig, new, original_values, intended, title_change=None):
    try:
        otree = wire.parse(orig)
        ntree = wire.parse(new)
    except wire.WireError as e:
        return False, "re-parse error: %s" % e

    # Everything except RTF leaves (and the title, if we changed it) must be
    # byte-identical.
    bt = title_change is not None
    if _blank_rtf_serialize(otree, bt) != _blank_rtf_serialize(ntree, bt):
        return False, "non-lyric structure changed"
    if title_change is not None:
        ntn = _find_title_node(ntree)
        if ntn is None or _title_bytes(ntn).decode("utf-8", "replace") != title_change[1]:
            return False, "title not set as intended"

    oleaves = wire.find_rtf_leaves(otree)
    nleaves = wire.find_rtf_leaves(ntree)
    if len(oleaves) != len(nleaves) != len(original_values):
        return False, "RTF leaf count changed"

    for idx, (_, nnode) in enumerate(nleaves):
        oval = original_values[idx]
        nval = nnode[2]
        if idx in intended:
            # changed leaf: must re-parse and yield exactly the corrected text
            got = rtf.extract(nval).text
            if got != intended[idx]:
                return False, "leaf %d text mismatch" % idx
        else:
            # untouched leaf: must be byte-identical
            if nval != oval:
                return False, "unintended change at leaf %d" % idx
    return True, "ok"
