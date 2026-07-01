"""Single, append-only, human-readable record of every lyric edit.

Both the always-on deterministic corrector (`monitor.py`) and the nightly AI
pass (`aibatch.py`) append here, so the repo holds ONE ongoing log of what was
changed in each song and why. Path: ``<repo>/EDIT-LOG.md`` (see
``config.changelog_path``). Newest entries are appended at the bottom.

This is deliberately fail-soft: logging must never block or undo a correction,
so any write error is swallowed.
"""

from __future__ import annotations
import os
import time

from . import config

_HEADER = (
    "# Lyric edit log\n\n"
    "Append-only record of every change made to a song in the ProPresenter\n"
    "Songs library -- by both the always-on deterministic corrector and the\n"
    "nightly AI pass. Newest entries are at the bottom. Generated; do not edit\n"
    "by hand.\n"
)


def _oneline(text: str) -> str:
    """Faithful single-line rendering: show line breaks as ' / '."""
    return text.replace("\n", " / ")


def append(path, source, edits, title_change=None, backup=None,
           changelog_path=None):
    """Append one song's edit as a markdown block.

    path          full ``.pro`` path of the edited song
    source        "deterministic" or "AI"
    edits         iterable of ``(slide_index, old_text, new_text, notes_list)``
    title_change  ``(old_title, new_title)`` or ``None``
    backup        backup file basename or ``None``
    """
    cp = changelog_path or config.changelog_path()
    name = os.path.basename(path)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")

    lines = ["", "### %s | %s | %s" % (stamp, name, source)]
    if backup:
        lines.append("- backup: `%s`" % backup)
    if title_change:
        lines.append("- title: `%s` -> `%s`" % title_change)
    for idx, old, new, notes in edits:
        why = ", ".join(notes) if notes else source
        lines.append("- slide %d (%s):" % (idx, why))
        lines.append("  - `%s` -> `%s`" % (_oneline(old), _oneline(new)))
    block = "\n".join(lines) + "\n"

    try:
        new_file = not os.path.exists(cp)
        d = os.path.dirname(cp)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(cp, "a", encoding="utf-8") as fh:
            if new_file:
                fh.write(_HEADER)
            fh.write(block)
    except OSError:
        pass
