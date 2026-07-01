"""The correction engine: scan, gate, correct, back up, atomically write, log.

Used by both `apply-once` (one pass) and `watch` (always-on poll loop). No third-
party dependencies -- the watcher polls file signatures so it runs reliably under
a LaunchAgent on the bare system Python.
"""

from __future__ import annotations
import hashlib
import json
import os
import time

from . import config, backup, song_gate, presentation, rules, changelog, reviewed


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Engine:
    def __init__(self, root, library=config.DEFAULT_LIBRARY, backup_dir=None,
                 cache_path=None, queue_path=None, cfg=None, dry_run=False,
                 override_while_open=False, verbose=False, logfile=None,
                 no_ai=True):
        self.root = root
        self.library = library
        self.backup_dir = backup_dir or config.default_backup_dir()
        self.cache_path = cache_path or config.default_cache_path()
        self.queue_path = queue_path or config.default_queue_path()
        self.reviewed_path = config.default_reviewed_path()
        self.cfg = cfg or rules.DEFAULT
        self.dry_run = dry_run
        self.override_while_open = override_while_open
        self.verbose = verbose
        self.no_ai = no_ai
        self.deferred = set()
        self._cache = self._load_cache()
        self.logfile = logfile or os.path.join(
            config.log_dir(), time.strftime("%Y-%m-%d") + ".log")
        os.makedirs(os.path.dirname(self.logfile), exist_ok=True)
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)

    # -- logging -----------------------------------------------------------
    def log(self, msg, level="INFO"):
        line = "%s %-5s %s" % (_now(), level, msg)
        try:
            with open(self.logfile, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass
        if self.verbose or level in ("WARN", "ERROR"):
            print(line)

    # -- cache -------------------------------------------------------------
    def _load_cache(self):
        try:
            with open(self.cache_path or "", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError, TypeError):
            return {}

    def _save_cache(self):
        try:
            tmp = self.cache_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._cache, fh)
            os.replace(tmp, self.cache_path)
        except OSError:
            pass

    # -- queue (for the optional AI pass) ----------------------------------
    def _enqueue_ambiguous(self, path, flags):
        if not flags:
            return
        try:
            os.makedirs(os.path.dirname(self.queue_path), exist_ok=True)
            with open(self.queue_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "time": _now(), "file": path, "flags": flags}) + "\n")
        except OSError:
            pass

    # -- core --------------------------------------------------------------
    def process_path(self, path, force=False):
        """Correct a single file. Returns a result dict for reporting."""
        name = os.path.basename(path)
        try:
            data = open(path, "rb").read()
        except OSError as e:
            self.log("skip %s (unreadable: %s)" % (name, e), "WARN")
            return {"file": path, "status": "error", "reason": str(e)}

        digest = _sha(data)
        entry = self._cache.get(path)
        if not force and entry and entry.get("hash") == digest \
                and entry.get("seen_clean"):
            return {"file": path, "status": "cached"}

        is_song, reason = song_gate.classify(path, data)
        if not is_song:
            self.log("skip %s (%s)" % (name, reason))
            self._cache[path] = {"hash": digest, "seen_clean": True,
                                 "skipped": reason}
            self._save_cache()
            return {"file": path, "status": "skipped", "reason": reason}

        desired_title = os.path.splitext(os.path.basename(path))[0]
        res = presentation.process_bytes(data, self.cfg,
                                         desired_title=desired_title)
        if res.error:
            self.log("skip %s (%s)" % (name, res.error), "WARN")
            self._cache[path] = {"hash": digest, "seen_clean": True,
                                 "error": res.error}
            self._save_cache()
            return {"file": path, "status": "error", "reason": res.error}

        # Queue for the AI pass ONLY if the lyrics changed since the AI last
        # reviewed this song -- so the nightly routine never re-runs the whole
        # library or re-reviews songs the correctors themselves just touched.
        if not reviewed.already_reviewed(path, data, reviewed.load(self.reviewed_path)):
            self._enqueue_ambiguous(path, res.flags)

        if not res.changed:
            self._cache[path] = {"hash": digest, "seen_clean": True}
            self._save_cache()
            return {"file": path, "status": "nochange",
                    "flags": res.flags, "lyric_slides": res.lyric_slides}

        if self.dry_run:
            return {"file": path, "status": "would-change", "result": res}

        # Fail-closed while ProPresenter is open.
        if config.is_propresenter_running() and not self.override_while_open:
            self.deferred.add(path)
            self.log("defer %s (ProPresenter is open; will retry)" % name)
            return {"file": path, "status": "deferred"}

        try:
            summary = {"changes": len(res.changes),
                       "notes": [c.notes for c in res.changes],
                       "title_change": res.title_change,
                       "skipped_dirty": res.skipped_dirty}
            bpath = backup.make_backup(path, self.backup_dir, summary)
            backup.atomic_write(path, res.new_bytes)
            # post-write re-verify
            check = presentation.process_bytes(open(path, "rb").read(), self.cfg)
            if check.error:
                self.log("POST-WRITE PARSE FAILED %s -> restoring backup" % name,
                         "ERROR")
                backup.atomic_write(path, open(bpath, "rb").read())
                return {"file": path, "status": "error",
                        "reason": "post-write verify failed; restored"}
        except Exception as e:  # noqa
            self.log("write failed %s (%s)" % (name, e), "ERROR")
            return {"file": path, "status": "error", "reason": str(e)}

        self._cache[path] = {"hash": _sha(res.new_bytes), "seen_clean": True}
        self._save_cache()
        self.deferred.discard(path)
        self.log("changed %s (%d edits%s, backup=%s)"
                 % (name, len(res.changes),
                    "; title->%r" % (res.title_change[1],) if res.title_change else "",
                    os.path.basename(bpath)))
        if res.title_change:
            self.log("    title: %r -> %r" % res.title_change)
        for c in res.changes:
            self.log("    [%d] %r -> %r" % (c.index, c.old_text, c.new_text))
        # Durable, in-repo record of what changed and why (fail-soft).
        changelog.append(
            path, "deterministic",
            [(c.index, c.old_text, c.new_text, c.notes) for c in res.changes],
            title_change=res.title_change,
            backup=os.path.basename(bpath))
        return {"file": path, "status": "changed", "result": res,
                "backup": bpath}

    def scan_once(self, force=False):
        files = config.list_song_files(self.root, self.library)
        results = []
        for f in files:
            try:
                sig = os.stat(f)
            except OSError:
                continue
            entry = self._cache.get(f)
            if not force and entry and entry.get("sig") == [sig.st_mtime, sig.st_size]:
                continue
            r = self.process_path(f, force=force)
            # remember cheap signature too
            self._cache.setdefault(f, {})["sig"] = [sig.st_mtime, sig.st_size]
            self._save_cache()
            results.append(r)
        return results

    def retry_deferred(self):
        if not self.deferred:
            return
        if config.is_propresenter_running() and not self.override_while_open:
            return
        for path in list(self.deferred):
            self.process_path(path, force=True)

    def watch(self, interval=5.0):
        self.log("watch start: library=%s interval=%ss override_while_open=%s"
                 % (os.path.join(self.root, "Libraries", self.library),
                    interval, self.override_while_open))
        try:
            while True:
                self.scan_once()
                self.retry_deferred()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.log("watch stop (interrupt)")
