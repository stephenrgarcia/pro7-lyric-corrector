"""Environment discovery: ProPresenter roots, the Songs library, exclusions,
ProPresenter-running detection, and cloud-sync warnings.

Nothing is hardcoded to a username. Roots are auto-detected and can be
overridden with --root.
"""

from __future__ import annotations
import os
import plistlib
import subprocess

HOME = os.path.expanduser("~")

# Candidate locations for the ProPresenter data root, in priority order.
_CANDIDATE_ROOTS = [
    os.path.join(HOME, "Documents", "ProPresenter"),
    os.path.join(HOME, "Library", "Application Support", "RenewedVision",
                 "ProPresenter", "User Workspaces"),
]

_SYNC_MARKERS = ("Dropbox", "Google Drive", "GoogleDrive", "OneDrive",
                 "com~apple~CloudDocs", "iCloud", "Library/Mobile Documents")

# Main app binary path fragment (NOT the helper processes, which are always up).
_PP_MAIN_BINARY = "ProPresenter.app/Contents/MacOS/ProPresenter"

DEFAULT_LIBRARY = "Songs"


def _is_pp_root(path: str) -> bool:
    return os.path.isdir(os.path.join(path, "Libraries"))


def _support_files_override():
    """Honor Settings -> Advanced -> Support Files relocation if recorded."""
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
    for c in _CANDIDATE_ROOTS:
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
            if name.endswith(".pro") and not name.startswith("."):
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
    low = path
    for marker in _SYNC_MARKERS:
        if marker in low:
            return marker
    return None


def is_propresenter_running() -> bool:
    """True only if the MAIN ProPresenter app is running (helpers ignored)."""
    try:
        res = subprocess.run(["pgrep", "-f", _PP_MAIN_BINARY],
                             capture_output=True, text=True, timeout=5)
        return res.returncode == 0 and res.stdout.strip() != ""
    except Exception:
        # Fail-closed: if we cannot tell, assume it IS running.
        return True


def default_backup_dir() -> str:
    return os.path.join(HOME, "Documents", "ProPresenter Backups",
                        "lyric-corrector")


def default_cache_path() -> str:
    return os.path.join(HOME, ".cache", "pro7_lyric_corrector", "state.json")


def default_queue_path() -> str:
    return os.path.join(HOME, ".cache", "pro7_lyric_corrector",
                        "ambiguous_queue.jsonl")


def default_reviewed_path() -> str:
    """Map of song path -> lyric fingerprint the AI pass last reviewed. Used to
    queue a song for the AI ONLY when its lyrics changed since that review."""
    return os.path.join(HOME, ".cache", "pro7_lyric_corrector",
                        "ai_reviewed.json")


def log_dir() -> str:
    return os.path.join(HOME, "Library", "Logs", "pro7_lyric_corrector")


def repo_dir() -> str:
    """Root of this checkout (parent of the pro7corrector package)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def changelog_path() -> str:
    """Single append-only edit log, kept in the repo (tracked; not a *.log)."""
    return os.path.join(repo_dir(), "EDIT-LOG.md")
