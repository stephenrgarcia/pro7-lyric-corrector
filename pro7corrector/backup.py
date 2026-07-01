"""Timestamped backups, an append-only manifest, atomic writes, and restore."""

from __future__ import annotations
import json
import os
import shutil
import tempfile
import time

MANIFEST = "manifest.jsonl"


def _ts():
    return time.strftime("%Y%m%d-%H%M%S")


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def make_backup(orig_path: str, backup_dir: str, summary=None) -> str:
    """Copy orig_path into backup_dir with a timestamp; append a manifest row."""
    ensure_dir(backup_dir)
    base = os.path.basename(orig_path)
    backup_name = "%s__%s.pro.bak" % (_ts(), base[:-4] if base.endswith(".pro") else base)
    backup_path = os.path.join(backup_dir, backup_name)
    # avoid clobber if two writes land in the same second
    n = 1
    while os.path.exists(backup_path):
        backup_path = os.path.join(backup_dir, "%s__%s__%d.pro.bak" % (_ts(), base, n))
        n += 1
    shutil.copy2(orig_path, backup_path)
    row = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "backup": backup_path,
        "original": orig_path,
        "summary": summary or {},
    }
    with open(os.path.join(backup_dir, MANIFEST), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return backup_path


def atomic_write(path: str, data: bytes):
    """Write data to a temp file in the same directory, then os.replace()."""
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".tmp_lyric_", dir=d)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        # preserve original mode if file exists
        try:
            st = os.stat(path)
            os.chmod(tmp, st.st_mode)
        except FileNotFoundError:
            pass
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def read_manifest(backup_dir: str):
    path = os.path.join(backup_dir, MANIFEST)
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return rows


def restore(backup_id_or_path: str, backup_dir: str) -> str:
    """Restore an original from a backup file path or basename."""
    candidate = backup_id_or_path
    if not os.path.exists(candidate):
        candidate = os.path.join(backup_dir, backup_id_or_path)
    if not os.path.exists(candidate):
        # search manifest by suffix match
        for row in reversed(read_manifest(backup_dir)):
            if row["backup"].endswith(backup_id_or_path):
                candidate = row["backup"]
                break
    if not os.path.exists(candidate):
        raise SystemExit("Backup not found: %s" % backup_id_or_path)
    # find original from manifest
    original = None
    for row in reversed(read_manifest(backup_dir)):
        if os.path.abspath(row["backup"]) == os.path.abspath(candidate):
            original = row["original"]
            break
    if not original:
        raise SystemExit("No manifest entry maps %s to an original." % candidate)
    atomic_write(original, open(candidate, "rb").read())
    return original
