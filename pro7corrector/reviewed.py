"""Track which song lyrics the AI pass has already reviewed.

The nightly AI routine should spend tokens ONLY on songs that are new or whose
lyrics changed since the AI last looked at them -- never the whole library. To
make that robust regardless of how the queue was filled (incremental watch,
a manual ``apply-once``, or the AI's own corrections), we fingerprint each
song's lyric text and remember the fingerprint the AI last reviewed.

A song is queued for the AI only when its current fingerprint differs from the
recorded one (or is absent = never reviewed). After the AI routine processes a
batch (``--clear-queue``), the current fingerprints are recorded as reviewed, so
those songs won't be re-queued until their lyrics actually change again.

Fail-soft: any error here must never block a correction; callers treat a missing
or unreadable map as "nothing reviewed yet" (i.e. fall back to queuing).
"""

from __future__ import annotations
import hashlib
import json
import os

from . import wire, rtf, config


def _slide_texts(data: bytes):
    """Clean, non-empty lyric slide texts -- the same content that drives flags
    and that the AI pass sees. Order-preserving."""
    out = []
    for _, node in wire.find_rtf_leaves(wire.parse(data)):
        pt = rtf.extract(node[2])
        if pt.text.strip() and pt.clean:
            out.append(pt.text)
    return out


def fingerprint(data: bytes):
    """Stable hash of a song's lyric text. None if it can't be computed (then
    callers fall back to queuing, the safe default)."""
    try:
        h = hashlib.sha256()
        for t in _slide_texts(data):
            h.update(t.encode("utf-8", "replace"))
            h.update(b"\x00")
        return h.hexdigest()
    except Exception:  # noqa - never let fingerprinting break a correction
        return None


def load(path=None) -> dict:
    path = path or config.default_reviewed_path()
    try:
        with open(path, encoding="utf-8") as fh:
            m = json.load(fh)
            return m if isinstance(m, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save(m: dict, path=None):
    path = path or config.default_reviewed_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(m, fh)
        os.replace(tmp, path)
    except OSError:
        pass


def already_reviewed(path: str, data: bytes, m: dict) -> bool:
    """True if this song's current lyrics match what the AI last reviewed."""
    fp = fingerprint(data)
    return fp is not None and m.get(path) == fp


def mark_reviewed(files, path=None):
    """Record the CURRENT lyric fingerprint of each file as AI-reviewed."""
    path = path or config.default_reviewed_path()
    m = load(path)
    for f in files:
        try:
            data = open(f, "rb").read()
        except OSError:
            continue
        fp = fingerprint(data)
        if fp:
            m[f] = fp
    save(m, path)
    return m
