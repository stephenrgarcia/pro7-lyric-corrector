"""Per-file song-detection gate.

The tool only ever scans the Songs library, but that library can still contain
the occasional non-song presentation (a sermon, an event slide, a spontaneous
worship placeholder). This gate keeps those out of the edit path.
"""

from __future__ import annotations
import os
import re

from . import wire, rtf

# Strong non-song name markers (case-insensitive, word-ish). Deliberately
# narrow: real worship songs contain words like "welcome", "offering", "notes",
# and spontaneous worship IS a song, so those are NOT markers -- the structural
# "has lyric slides" check is the real safety net for anything that slips
# through.
_SKIP_NAME = re.compile(
    r"\b(sermon|message|announcement|pre-?post)\b|\bevent\b", re.I)

# Song-section words that, if present as group/arrangement labels, boost
# confidence that a file is a song.
_SECTION_WORDS = re.compile(
    r"\b(verse|chorus|bridge|pre-?chorus|tag|interlude|refrain|vamp|"
    r"intro|outro|ending|turnaround)\b", re.I)


def classify(path: str, data: bytes = None):
    """Return (is_song: bool, reason: str).

    is_song True  -> safe to correct.
    is_song False -> skip and log `reason`.
    """
    name = os.path.basename(path)
    if name.startswith("."):
        return False, "hidden file"
    if not name.lower().endswith(".pro"):
        return False, "not a .pro file"
    if _SKIP_NAME.search(name):
        return False, "name matches non-song marker"

    if data is None:
        try:
            data = open(path, "rb").read()
        except OSError as e:
            return False, "unreadable: %s" % e
    try:
        tree = wire.parse(data)
    except wire.WireError as e:
        return False, "not valid PP7 protobuf: %s" % e

    lyric_slides = 0
    for _, node in wire.find_rtf_leaves(tree):
        if rtf.extract(node[2]).text.strip():
            lyric_slides += 1
    if lyric_slides == 0:
        return False, "no lyric text slides"

    return True, "song (%d lyric slides)" % lyric_slides


def has_section_labels(data: bytes) -> bool:
    try:
        tree = wire.parse(data)
    except wire.WireError:
        return False
    for _, text in wire.find_string_leaves(tree):
        if _SECTION_WORDS.search(text):
            return True
    return False
