"""macOS LaunchAgent install / start / stop / status for the always-on monitor."""

from __future__ import annotations
import os
import subprocess
import sys

from . import config

LABEL = "com.reach.pro7lyriccorrector"


def plist_path():
    return os.path.join(config.HOME, "Library", "LaunchAgents", LABEL + ".plist")


def _xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_plist(python_exe, script, root, library, interval=5,
                override_while_open=False):
    # `watch` is deterministic-only by construction (it never calls the AI pass),
    # so no --no-ai flag is needed -- and a top-level flag placed AFTER the
    # subcommand makes argparse error ("unrecognized arguments: --no-ai"), which
    # would crash the agent on every launch. Pass only options `watch` accepts.
    args = [python_exe, script, "watch",
            "--root", root, "--library", library,
            "--interval", str(interval)]
    if override_while_open:
        args.append("--override-while-open")
    out_log = os.path.join(config.log_dir(), "agent.out.log")
    err_log = os.path.join(config.log_dir(), "agent.err.log")
    items = "\n".join("        <string>%s</string>" % _xml_escape(a) for a in args)
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" \
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
{items}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>30</integer>
    <key>ProcessType</key>
    <string>Background</string>
    <key>StandardOutPath</key>
    <string>{out}</string>
    <key>StandardErrorPath</key>
    <string>{err}</string>
</dict>
</plist>
""".format(label=LABEL, items=items, out=_xml_escape(out_log),
           err=_xml_escape(err_log))


def install(python_exe, script, root, library, interval=5,
            override_while_open=False):
    os.makedirs(os.path.dirname(plist_path()), exist_ok=True)
    os.makedirs(config.log_dir(), exist_ok=True)
    text = build_plist(python_exe, script, root, library, interval,
                       override_while_open)
    with open(plist_path(), "w", encoding="utf-8") as fh:
        fh.write(text)
    return plist_path()


def _launchctl(*args):
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


def start():
    p = plist_path()
    if not os.path.exists(p):
        raise SystemExit("Plist not installed. Run install-agent first.")
    uid = os.getuid()
    # modern path first, fall back to legacy load
    r = _launchctl("bootstrap", "gui/%d" % uid, p)
    if r.returncode != 0 and "already" not in (r.stderr or "").lower():
        _launchctl("load", "-w", p)
    _launchctl("enable", "gui/%d/%s" % (uid, LABEL))
    _launchctl("kickstart", "gui/%d/%s" % (uid, LABEL))
    return status()


def stop():
    p = plist_path()
    uid = os.getuid()
    r = _launchctl("bootout", "gui/%d/%s" % (uid, LABEL))
    if r.returncode != 0:
        _launchctl("unload", p)
    return "stopped"


def status():
    uid = os.getuid()
    r = _launchctl("print", "gui/%d/%s" % (uid, LABEL))
    if r.returncode == 0:
        running = "state = running" in r.stdout
        pid = None
        for line in r.stdout.splitlines():
            if "pid =" in line:
                pid = line.split("=")[-1].strip()
                break
        return "installed; %s%s" % (
            "running" if running else "loaded",
            (" pid=%s" % pid) if pid else "")
    # fall back to list
    r2 = _launchctl("list")
    if LABEL in (r2.stdout or ""):
        return "loaded (via launchctl list)"
    return "not loaded"
