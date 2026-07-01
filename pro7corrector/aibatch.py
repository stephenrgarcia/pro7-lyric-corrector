"""Optional AI pass, driven by the nightly Claude Code routine.

The Python tool never calls a paid API. Instead it does two jobs:

  emit_tasks()       -> read the deterministic monitor's "ambiguous" queue and
                        print, per song, a strict-JSON task (title, sections,
                        slide indices, exact slide text, and the §8 rules). The
                        Claude Code routine reads this, reasons over each song,
                        and writes a proposals JSON.

  apply_proposals()  -> read that proposals JSON (slide index -> corrected
                        text), validate hard (no paraphrase / slide-count /
                        structure / length-delta checks), back up, and apply
                        atomically via the same verified pipeline.

This keeps all the dangerous file-writing logic in audited Python; the model
only ever supplies candidate text, which is validated before it touches disk.
"""

from __future__ import annotations
import json
import os

from . import wire, rtf, backup, presentation, config, changelog, reviewed

RULES_TEXT = (
    "Correct ONE song. Apply only conservative worship-lyric corrections: "
    "ambiguous divine capitalization (spirit/Spirit, word/Word, name/Name, "
    "father/Father, son/Son, king/King, lamb/Lamb, etc.) capitalized ONLY when "
    "the referent is clearly God/Jesus; otherwise leave lowercase. Do NOT "
    "paraphrase, rewrite, reorder, add or remove lines, or change meaning. "
    "Return STRICT JSON only: {\"file\": <path>, \"slides\": {<index>: <text>}} "
    "containing ONLY slides you changed, with line breaks as \\n."
)

# Length delta beyond which an AI proposal is rejected outright.
_MAX_DELTA_FRACTION = 0.5
_MAX_DELTA_CHARS = 60


def _queued_files(queue_path):
    files = []
    seen = set()
    if os.path.exists(queue_path):
        with open(queue_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                f = row.get("file")
                if f and f not in seen and os.path.exists(f):
                    seen.add(f)
                    files.append(f)
    return files


def slide_texts(data: bytes):
    """Return [(leaf_index, text)] for non-empty clean lyric slides."""
    tree = wire.parse(data)
    out = []
    for idx, (_, node) in enumerate(wire.find_rtf_leaves(tree)):
        pt = rtf.extract(node[2])
        if pt.text.strip() and pt.clean:
            out.append((idx, pt.text))
    return out


def emit_tasks(queue_path=None):
    queue_path = queue_path or config.default_queue_path()
    tasks = []
    for f in _queued_files(queue_path):
        try:
            data = open(f, "rb").read()
        except OSError:
            continue
        slides = slide_texts(data)
        if not slides:
            continue
        title = os.path.splitext(os.path.basename(f))[0]
        tasks.append({
            "file": f,
            "title": title,
            "rules": RULES_TEXT,
            "slides": [{"index": i, "text": t} for i, t in slides],
        })
    print(json.dumps({"tasks": tasks}, ensure_ascii=False, indent=2))
    return tasks


def _validate(old: str, new: str):
    if new == old:
        return False, "no change"
    delta = abs(len(new) - len(old))
    if delta > _MAX_DELTA_CHARS and delta / max(len(old), 1) > _MAX_DELTA_FRACTION:
        return False, "suspicious length delta"
    if old.count("\n") != new.count("\n"):
        return False, "line-break count changed"
    # reject reordering / wholesale rewrite: require word-set overlap
    ow = set(w.lower().strip(".,!?;:'\"") for w in old.split())
    nw = set(w.lower().strip(".,!?;:'\"") for w in new.split())
    if ow and len(ow & nw) / len(ow) < 0.5:
        return False, "too different (possible paraphrase)"
    return True, "ok"


def apply_proposals(proposals_path, root=None, library=config.DEFAULT_LIBRARY,
                    backup_dir=None, dry_run=False, verbose=False):
    backup_dir = backup_dir or config.default_backup_dir()
    with open(proposals_path, encoding="utf-8") as fh:
        payload = json.load(fh)
    items = payload if isinstance(payload, list) else [payload]
    applied = 0
    for item in items:
        f = item["file"]
        slides = {int(k): v for k, v in item["slides"].items()}
        if config.is_propresenter_running():
            print("DEFER (ProPresenter open): %s" % f)
            continue
        data = open(f, "rb").read()
        tree = wire.parse(data)
        leaves = wire.find_rtf_leaves(tree)
        intended = {}
        edit_rows = []  # (idx, old_text, new_text) for the in-repo edit log
        for idx, new_text in slides.items():
            if idx < 0 or idx >= len(leaves):
                print("  reject %s slide %d: out of range" % (f, idx))
                continue
            node = leaves[idx][1]
            parsed = rtf.extract(node[2])
            if not parsed.clean:
                print("  reject %s slide %d: not a clean lyric box" % (f, idx))
                continue
            ok, why = _validate(parsed.text, new_text)
            if not ok:
                print("  reject %s slide %d: %s" % (f, idx, why))
                continue
            node[2] = rtf.splice(node[2], new_text, parsed)
            intended[idx] = new_text
            edit_rows.append((idx, parsed.text, new_text))
        if not intended:
            continue
        new_bytes = wire.serialize(tree)
        # reuse the same structural verification used by the deterministic path
        ok, reason = presentation._verify(
            data, new_bytes,
            [n[2] for _, n in wire.find_rtf_leaves(wire.parse(data))], intended)
        if not ok:
            print("  reject %s: verification failed (%s)" % (f, reason))
            continue
        if dry_run:
            print("  would apply %d AI edits to %s" % (len(intended), f))
            applied += len(intended)
            continue
        bpath = backup.make_backup(f, backup_dir, {"ai_edits": len(intended)})
        backup.atomic_write(f, new_bytes)
        print("  applied %d AI edits to %s" % (len(intended), f))
        # Durable, in-repo record alongside the deterministic edits (fail-soft).
        changelog.append(
            f, "AI",
            [(i, old, new, ["AI-contextual"]) for i, old, new in edit_rows],
            backup=os.path.basename(bpath))
        applied += len(intended)
    return applied


def clear_queue(queue_path=None):
    queue_path = queue_path or config.default_queue_path()
    # Record the queued songs' CURRENT lyrics as AI-reviewed before clearing, so
    # the deterministic watcher won't re-queue them until their lyrics change
    # again (prevents the nightly routine from re-reviewing the whole library or
    # the songs the AI itself just corrected).
    reviewed.mark_reviewed(_queued_files(queue_path))
    if os.path.exists(queue_path):
        os.remove(queue_path)
