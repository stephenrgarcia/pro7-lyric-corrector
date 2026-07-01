"""Environment discovery: ProPresenter roots, the Songs library, exclusions,
ProPresenter-running detection, and cloud-sync warnings.

Nothing is hardcoded to a username. Roots are auto-detected and can be
overridden with --root.
"""

from __future__ import annotations
import os
import plistlib
import subprocess
import sys

HOME = os.path.expanduser("~")

_SYNC_MARKERS = ("Dropbox", "Google Drive", "GoogleDrive", "OneDrive",
                 "com~apple~CloudDocs", "iCloud", "Library/Mobile Documents")

# Main app binary path fragment (NOT the helper processes, which are always up).
_PP_MAIN_BINARY_MAC = "ProPresenter.app/Contents/MacOS/ProPresenter"
_PP_MAIN_BINARY_WIN = "ProPresenter.exe"

DEFAULT_LIBRARY = "Songs"


def _is_windows() -> bool:
    return os.name == "nt"


def _is_macos() -> bool:
    return sys.platform == "darwin"


def _is_pp_root(path: str) -> bool:
    return os.path.isdir(os.path.join(path, "Libraries"))


def _documents_dirs():
    """Likely user Documents folders across macOS and Windows.

    ProPresenter's default data root is typically Documents/ProPresenter. On
    Windows, Documents is often redirected into OneDrive, so include those
    common environment roots as well.
    """
    out = []
    seen = set()

    def add(p):
        if not p:
            return
        p = os.path.abspath(os.path.expanduser(p))
        if p not in seen:
            seen.add(p)
            out.append(p)

    add(os.path.join(HOME, "Documents"))
    if _is_windows():
        for env in ("USERPROFILE", "OneDrive", "OneDriveConsumer",
                    "OneDriveCommercial"):
            base = os.environ.get(env)
            if base:
                add(os.path.join(base, "Documents"))
    return out


def _candidate_roots():
    roots = []
    for doc in _documents_dirs():
        roots.append(os.path.join(doc, "ProPresenter"))
    if _is_macos():
        roots.append(os.path.join(HOME, "Library", "Application Support",
                                  "RenewedVision", "ProPresenter",
                                  "User Workspaces"))
    elif _is_windows():
        for env in ("APPDATA", "LOCALAPPDATA", "PROGRAMDATA"):
            base = os.environ.get(env)
            if not base:
                continue
            roots.extend([
                os.path.join(base, "RenewedVision", "ProPresenter",
                             "User Workspaces"),
                os.path.join(base, "Renewed Vision", "ProPresenter",
                             "User Workspaces"),
            ])
    return roots


def _support_files_override():
    """Honor Settings -> Advanced -> Support Files relocation if recorded."""
    if not _is_macos():
        return None
    prefs = os.path.join(HOME, "Library", "Preferences",
                         "com.renewedvision.ProPresenter7.plist")
    try:
        with open(prefs, "rb") as fh:
            data = plistlib.load(fh)
    except Exception:
        return None
    for key in ("applicationShowDirectory", "supportFilesDirectory",
                "libraryDirectory", "ApplicationSupportPath"):
        val = data.get(key)
        if isinstance(val, str) and os.path.isdir(val) and _is_pp_root(val):
            return val
    return None


def detect_roots(explicit=None):
    """Return a de-duplicated list of existing ProPresenter roots."""
    roots = []
    seen = set()

    def add(p):
        if not p:
            return
        p = os.path.abspath(os.path.expanduser(p))
        if p not in seen and _is_pp_root(p):
            seen.add(p)
            roots.append(p)

    add(explicit)
    add(_support_files_override())
    for c in _candidate_roots():
        add(c)
    return roots


def choose_root(explicit=None):
    roots = detect_roots(explicit)
    if not roots:
        raise SystemExit(
            "No ProPresenter root found. Pass --root /path/to/ProPresenter "
            "(the folder containing 'Libraries').")
    return roots[0]


def list_libraries(root: str):
    libdir = os.path.join(root, "Libraries")
    out = []
    if os.path.isdir(libdir):
        for name in sorted(os.listdir(libdir)):
            full = os.path.join(libdir, name)
            if os.path.isdir(full):
                out.append(name)
    return out


def songs_library_path(root: str, library: str = DEFAULT_LIBRARY) -> str:
    return os.path.join(root, "Libraries", library)


def list_song_files(root: str, library: str = DEFAULT_LIBRARY):
    """Return sorted .pro paths in the chosen library (non-recursive)."""
    path = songs_library_path(root, library)
    out = []
    if os.path.isdir(path):
        for name in sorted(os.listdir(path)):
            if name.lower().endswith(".pro") and not name.startswith("."):
                out.append(os.path.join(path, name))
    return out


def excluded_paths(root: str, library: str = DEFAULT_LIBRARY):
    """Sibling areas that must never be touched."""
    out = []
    for sib in ("Presets", "Playlists", "Themes", "Media", "Configuration",
                "Workflows", "Downloads"):
        p = os.path.join(root, sib)
        if os.path.exists(p):
            out.append(p)
    for lib in list_libraries(root):
        if lib != library:
            out.append(os.path.join(root, "Libraries", lib))
    return out


def is_in_sync_folder(path: str):
    low = path.lower()
    for marker in _SYNC_MARKERS:
        if marker.lower() in low:
            return marker
    return None


def is_propresenter_running() -> bool:
    """True only if the MAIN ProPresenter app is running (helpers ignored)."""
    if _is_windows():
        try:
            res = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq %s" % _PP_MAIN_BINARY_WIN,
                 "/NH"],
                capture_output=True, text=True, timeout=5)
            return _PP_MAIN_BINARY_WIN.lower() in (res.stdout or "").lower()
        except Exception:
            # Fail-closed: if we cannot tell, assume it IS running.
            return True
    if not _is_macos():
        # ProPresenter 7 is only supported here on macOS/Windows. Unknown
        # platforms should never write live files by accident.
        return True
    try:
        res = subprocess.run(["pgrep", "-f", _PP_MAIN_BINARY_MAC],
                             capture_output=True, text=True, timeout=5)
        return res.returncode == 0 and res.stdout.strip() != ""
    except Exception:
        # Fail-closed: if we cannot tell, assume it IS running.
        return True


def default_backup_dir() -> str:
    return os.path.join(HOME, "Documents", "ProPresenter Backups",
                        "lyric-corrector")


def default_cache_path() -> str:
    return os.path.join(_state_dir(), "state.json")


def default_queue_path() -> str:
    return os.path.join(_state_dir(), "ambiguous_queue.jsonl")


def default_reviewed_path() -> str:
    """Map of song path -> lyric fingerprint the AI pass last reviewed. Used to
    queue a song for the AI ONLY when its lyrics changed since that review."""
    return os.path.join(_state_dir(), "ai_reviewed.json")


def log_dir() -> str:
    if _is_windows():
        return os.path.join(_state_dir(), "logs")
    if _is_macos():
        return os.path.join(HOME, "Library", "Logs", "pro7_lyric_corrector")
    return os.path.join(_state_dir(), "logs")


def _state_dir() -> str:
    if _is_windows():
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or HOME
        return os.path.join(base, "pro7_lyric_corrector")
    if _is_macos():
        return os.path.join(HOME, ".cache", "pro7_lyric_corrector")
    return os.path.join(HOME, ".cache", "pro7_lyric_corrector")


def repo_dir() -> str:
    """Root of this checkout (parent of the pro7corrector package)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def changelog_path() -> str:
    """Single append-only edit log, kept in the repo (tracked; not a *.log)."""
    return os.path.join(repo_dir(), "EDIT-LOG.md")
