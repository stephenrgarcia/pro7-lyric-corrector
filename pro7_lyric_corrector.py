#!/usr/bin/env python3
"""pro7_lyric_corrector -- ProPresenter 7 worship-lyric autocorrector.

Songs-library-only. Deterministic, dependency-free correction engine plus an
optional AI pass for ambiguous theological capitalization.

Run `pro7_lyric_corrector.py <command> --help`.
"""

from __future__ import annotations
import argparse
import difflib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pro7corrector import (  # noqa: E402
    config, wire, rtf, rules, song_gate, presentation, backup, monitor,
    agent, aibatch)


def _cfg_from_args(args):
    return rules.Config()


def _engine(args):
    root = config.choose_root(getattr(args, "root", None))
    return monitor.Engine(
        root=root,
        library=args.library,
        backup_dir=args.backup_dir,
        cache_path=args.cache,
        cfg=_cfg_from_args(args),
        dry_run=getattr(args, "dry_run", False),
        override_while_open=getattr(args, "override_while_open", False),
        verbose=args.verbose,
        no_ai=getattr(args, "no_ai", True),
    )


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_discover(args):
    roots = config.detect_roots(args.root)
    if not roots:
        print("No ProPresenter root found. Pass --root /path/to/ProPresenter.")
        return 1
    root = roots[0]
    print("ProPresenter root(s) detected:")
    for r in roots:
        marker = "  <- chosen" if r == root else ""
        print("   %s%s" % (r, marker))
    sync = config.is_in_sync_folder(root)
    if sync:
        print("\n!! WARNING: root is inside a cloud-sync folder (%s)." % sync)
        print("   ProPresenter data should NOT live in iCloud/Dropbox/etc.")
    print("\nLibraries under chosen root:")
    for lib in config.list_libraries(root):
        flag = "  (SELECTED)" if lib == args.library else "  (excluded)"
        print("   %s%s" % (lib, flag))
    songs_path = config.songs_library_path(root, args.library)
    print("\nChosen Songs library:\n   %s" % songs_path)
    print("   reason: it is Libraries/%s -- the song slides library; sermons, "
          "announcements, playlists, themes, media, and other libraries are "
          "excluded." % args.library)
    print("\nExcluded (never touched):")
    for p in config.excluded_paths(root, args.library):
        print("   %s" % p)
    files = config.list_song_files(root, args.library)
    songs, skipped = [], []
    for f in files:
        ok, reason = song_gate.classify(f)
        (songs if ok else skipped).append((f, reason))
    print("\nSelected song .pro files: %d" % len(songs))
    for f, _ in songs[:15]:
        print("   %s" % os.path.basename(f))
    if len(songs) > 15:
        print("   ... (%d more)" % (len(songs) - 15))
    print("\nNon-song files skipped inside Songs: %d" % len(skipped))
    for f, reason in skipped:
        print("   %s  (%s)" % (os.path.basename(f), reason))
    return 0


def cmd_inspect(args):
    path = args.file
    data = open(path, "rb").read()
    tree = wire.parse(data)
    title = presentation.presentation_title(tree, path)
    print("File : %s" % path)
    print("Title: %s" % (title or "(unknown)"))
    is_song, reason = song_gate.classify(path, data)
    print("Gate : %s (%s)" % ("SONG" if is_song else "SKIP", reason))
    print("\nLyric slides:")
    for idx, (p, node) in enumerate(wire.find_rtf_leaves(tree)):
        pt = rtf.extract(node[2])
        if not pt.text.strip():
            continue
        tag = "" if pt.clean else "  [interleaved-skip]"
        shown = pt.text.replace("\n", " / ")
        print("   [%2d]%s %s" % (idx, tag, shown))
    return 0


def _unified(old, new, label):
    return "\n".join(difflib.unified_diff(
        old.split("\n"), new.split("\n"),
        fromfile=label + " (before)", tofile=label + " (after)", lineterm=""))


def _print_result_preview(path, res, per_file=0):
    """Print every proposed edit for one song unless per_file caps it."""
    print("=" * 70)
    print("%s  (%d edits, %d flagged-ambiguous)"
          % (os.path.basename(path), len(res.changes), len(res.flags)))
    if res.title_change:
        print("  title: %r -> %r" % res.title_change)
    changes = res.changes if per_file == 0 else res.changes[:per_file]
    for c in changes:
        print(_unified(c.old_text, c.new_text, "slide %d" % c.index))
    if per_file and len(res.changes) > per_file:
        print("  ... %d more slide edits hidden (use --per-file 0 to show all)"
              % (len(res.changes) - per_file))
    if res.flags:
        print("  flags:", ", ".join(sorted(set(res.flags))[:8]))


def _ask(prompt, default="n"):
    suffix = " [%s] " % default.upper() if default else " "
    try:
        ans = input(prompt + suffix).strip().lower()
    except EOFError:
        return default
    return ans or default


def cmd_calibrate(args):
    root = config.choose_root(args.root)
    print("Calibration / dry-run (NO files will be written)")
    print("Songs library: %s\n" % config.songs_library_path(root, args.library))
    files = config.list_song_files(root, args.library)
    if args.file:
        files = [args.file]
    limit = None if args.all else args.limit
    shown = 0
    total_changes = 0
    cat = {}
    for f in files:
        data = open(f, "rb").read()
        ok, reason = song_gate.classify(f, data)
        if not ok:
            continue
        stem = os.path.splitext(os.path.basename(f))[0]
        res = presentation.process_bytes(data, _cfg_from_args(args),
                                         desired_title=stem)
        if res.error or not res.changed:
            continue
        total_changes += len(res.changes)
        if res.title_change:
            cat["title-fix"] = cat.get("title-fix", 0) + 1
        for c in res.changes:
            for n in c.notes:
                key = n.split(":")[0]
                cat[key] = cat.get(key, 0) + 1
        if limit is None or shown < limit:
            _print_result_preview(f, res, args.per_file)
            shown += 1
    print("=" * 70)
    if limit is None:
        print("Songs that would change shown above (all).")
    else:
        print("Songs that would change shown above (first %d)." % args.limit)
    print("Total proposed edits across library: %d" % total_changes)
    print("Edit categories:")
    for k, v in sorted(cat.items(), key=lambda x: -x[1]):
        print("   %-22s %d" % (k, v))
    return 0


def cmd_review(args):
    root = config.choose_root(args.root)
    print("Interactive review (NO files are written until final confirmation)")
    print("Songs library: %s\n" % config.songs_library_path(root, args.library))
    files = config.list_song_files(root, args.library)
    if args.file:
        files = [args.file]

    approved = []
    proposed = 0
    stop_review = False
    for f in files:
        try:
            data = open(f, "rb").read()
        except OSError as e:
            print("SKIP %s (unreadable: %s)" % (os.path.basename(f), e))
            continue
        ok, _ = song_gate.classify(f, data)
        if not ok:
            continue
        stem = os.path.splitext(os.path.basename(f))[0]
        res = presentation.process_bytes(data, _cfg_from_args(args),
                                         desired_title=stem)
        if res.error:
            print("SKIP %s (%s)" % (os.path.basename(f), res.error))
            continue
        if not res.changed:
            continue
        proposed += 1
        _print_result_preview(f, res, args.per_file)
        while True:
            ans = _ask("Approve this song? y=yes, n=skip, q=finish review", "n")
            if ans in ("y", "yes"):
                approved.append((f, data))
                break
            if ans in ("n", "no", "s", "skip"):
                break
            if ans in ("q", "quit", "done"):
                stop_review = True
                break
            print("Please answer y, n, or q.")
        if stop_review:
            break

    print("=" * 70)
    print("Review complete. Proposed: %d   Approved: %d   Skipped: %d"
          % (proposed, len(approved), proposed - len(approved)))
    if not approved:
        print("No files approved; nothing written.")
        return 0
    ans = _ask("Write approved changes to the live Songs library now?", "n")
    if ans not in ("y", "yes"):
        print("Nothing written.")
        return 0

    eng = _engine(args)
    if config.is_propresenter_running() and not args.override_while_open:
        print("NOTE: ProPresenter is open; approved files will be DEFERRED "
              "(fail-closed). Quit ProPresenter and run again to write.")
    changed = deferred = skipped = errors = 0
    for path, reviewed_data in approved:
        try:
            current_data = open(path, "rb").read()
        except OSError as e:
            errors += 1
            print("  ERROR %s (%s)" % (os.path.basename(path), e))
            continue
        if current_data != reviewed_data:
            skipped += 1
            print("  SKIP %s (file changed after review; re-run review)"
                  % os.path.basename(path))
            continue
        r = eng.process_path(path, force=True)
        status = r["status"]
        if status == "changed":
            changed += 1
            print("  CHANGED %s  (%d edits) backup=%s"
                  % (os.path.basename(path), len(r["result"].changes),
                     os.path.basename(r["backup"])))
        elif status == "deferred":
            deferred += 1
            print("  DEFERRED %s" % os.path.basename(path))
        elif status in ("skipped", "nochange", "cached"):
            skipped += 1
            print("  SKIP %s (%s)" % (os.path.basename(path), status))
        else:
            errors += 1
            print("  ERROR %s (%s)" % (os.path.basename(path),
                                      r.get("reason", status)))
    print("\nChanged: %d   Deferred: %d   Skipped: %d   Errors: %d"
          % (changed, deferred, skipped, errors))
    return 0


def cmd_apply_once(args):
    if getattr(args, "review", False):
        return cmd_review(args)
    eng = _engine(args)
    print("apply-once on %s" % config.songs_library_path(eng.root, eng.library))
    if config.is_propresenter_running() and not args.override_while_open:
        print("NOTE: ProPresenter is open; changed files will be DEFERRED "
              "(fail-closed). Use --override-while-open to force (risky).")
    results = eng.scan_once(force=True)
    changed = [r for r in results if r["status"] == "changed"]
    deferred = [r for r in results if r["status"] == "deferred"]
    skipped = [r for r in results if r["status"] == "skipped"]
    errors = [r for r in results if r["status"] == "error"]
    print("\nChanged: %d   Deferred: %d   Skipped(non-song): %d   Errors: %d"
          % (len(changed), len(deferred), len(skipped), len(errors)))
    for r in changed:
        print("  CHANGED %s  (%d edits) backup=%s"
              % (os.path.basename(r["file"]), len(r["result"].changes),
                 os.path.basename(r["backup"])))
    for r in deferred:
        print("  DEFERRED %s" % os.path.basename(r["file"]))
    return 0


def cmd_watch(args):
    eng = _engine(args)
    eng.verbose = True
    eng.watch(interval=args.interval)
    return 0


def cmd_install_agent(args):
    root = config.choose_root(args.root)
    script = os.path.abspath(__file__)
    # On macOS prefer the stable system interpreter path -- it is the one the
    # user grants Full Disk Access to in System Settings. On Windows, use the
    # interpreter running this installer so Task Scheduler points at a real exe.
    py = ("/usr/bin/python3" if config._is_macos()
          and os.path.exists("/usr/bin/python3") else sys.executable)
    p = agent.install(py, script, root, args.library,
                      interval=args.interval,
                      override_while_open=args.override_while_open)
    print("Installed background helper: %s" % p)
    print("Scoped to: %s" % config.songs_library_path(root, args.library))
    print("Start it with:  %s start" % os.path.basename(script))
    return 0


def cmd_start(args):
    print(agent.start())
    return 0


def cmd_stop(args):
    print(agent.stop())
    return 0


def cmd_status(args):
    print("Background helper: %s" % agent.status())
    print("ProPresenter running: %s" % config.is_propresenter_running())
    return 0


def cmd_ai_batch(args):
    if args.apply:
        root = config.choose_root(args.root)
        n = aibatch.apply_proposals(args.apply, root=root, library=args.library,
                                    backup_dir=args.backup_dir,
                                    dry_run=args.dry_run, verbose=args.verbose)
        print("AI edits applied: %d" % n)
        if not args.dry_run and args.clear_queue:
            aibatch.clear_queue(args.queue)
    else:
        aibatch.emit_tasks(args.queue)
    return 0


def cmd_restore(args):
    original = backup.restore(args.restore, args.backup_dir)
    print("Restored: %s" % original)
    return 0


# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------

def _add_shared(parser, suppress):
    """Shared options. On the main parser they carry real defaults; on each
    subparser they default to SUPPRESS so an unset subparser copy never clobbers
    a value already parsed before the subcommand. Net effect: these options work
    in either position (`--root X apply-once` or `apply-once --root X`)."""
    S = argparse.SUPPRESS
    parser.add_argument("--root", default=(S if suppress else None),
                        help="ProPresenter root (auto-detected if omitted)")
    parser.add_argument("--library", default=(S if suppress else config.DEFAULT_LIBRARY))
    parser.add_argument("--backup-dir", default=(S if suppress else config.default_backup_dir()))
    parser.add_argument("--cache", default=(S if suppress else config.default_cache_path()))
    parser.add_argument("--queue", default=(S if suppress else config.default_queue_path()))
    parser.add_argument("--verbose", action="store_true",
                        default=(S if suppress else False))


def build_parser():
    p = argparse.ArgumentParser(prog="pro7_lyric_corrector.py",
                                description=__doc__)
    _add_shared(p, suppress=False)
    p.add_argument("--no-ai", action="store_true", default=True)
    p.add_argument("--restore", help="restore a file from a backup id/path")

    sub = p.add_subparsers(dest="command")

    def add(name, **kw):
        sp = sub.add_parser(name, **kw)
        _add_shared(sp, suppress=True)
        return sp

    add("discover")

    sp = add("inspect")
    sp.add_argument("file")

    sp = add("calibrate", aliases=["dry-run"])
    sp.add_argument("--file", help="calibrate a single file")
    sp.add_argument("--limit", type=int, default=12, help="songs to show")
    sp.add_argument("--all", action="store_true", help="show every changed song")
    sp.add_argument("--per-file", type=int, default=6,
                    help="edits per song; 0 shows every edit")
    sp.add_argument("--dry-run", action="store_true", default=True)

    sp = add("review")
    sp.add_argument("--file", help="review a single file")
    sp.add_argument("--per-file", type=int, default=0,
                    help="edits per song; 0 shows every edit")
    sp.add_argument("--override-while-open", action="store_true")

    sp = add("apply-once")
    sp.add_argument("--override-while-open", action="store_true")
    sp.add_argument("--review", action="store_true",
                    help="review each proposed song before writing")

    sp = add("watch")
    sp.add_argument("--interval", type=float, default=5.0)
    sp.add_argument("--override-while-open", action="store_true")

    sp = add("install-agent")
    sp.add_argument("--interval", type=float, default=5.0)
    sp.add_argument("--override-while-open", action="store_true")

    add("start")
    add("stop")
    add("status")

    sp = add("ai-batch")
    sp.add_argument("--apply", help="apply a proposals JSON file")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--clear-queue", action="store_true")

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.restore:
        return cmd_restore(args)
    dispatch = {
        "discover": cmd_discover, "inspect": cmd_inspect,
        "calibrate": cmd_calibrate, "dry-run": cmd_calibrate,
        "review": cmd_review, "apply-once": cmd_apply_once, "watch": cmd_watch,
        "install-agent": cmd_install_agent, "start": cmd_start,
        "stop": cmd_stop, "status": cmd_status, "ai-batch": cmd_ai_batch,
    }
    fn = dispatch.get(args.command)
    if not fn:
        build_parser().print_help()
        return 1
    return fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
