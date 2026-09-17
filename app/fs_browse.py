"""Server-side filesystem browser backing the dashboard's video file picker.

The app never uploads/copies videos - the user just needs to point at a path
on the machine running the server, so instead of an `<input type="file">`
(which browsers refuse to reveal the real absolute path for) the UI lets the
user browse this machine's filesystem and the server hands back full paths.
"""
from __future__ import annotations

import os
import string
from pathlib import Path

from app.config import ALLOWED_AUDIO_EXTENSIONS, ALLOWED_TEXT_EXTENSIONS, ALLOWED_VIDEO_EXTENSIONS


def _windows_drives() -> list[dict]:
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            drives.append({"name": drive, "path": drive, "is_dir": True})
    return drives


def list_directory(path: str | None, kind: str = "video") -> dict:
    """Returns {"path", "parent", "entries"} for the given directory, or the
    list of drives (Windows) / filesystem root (other OSes) when path is empty."""
    extensions = {
        "video": ALLOWED_VIDEO_EXTENSIONS,
        "audio": ALLOWED_AUDIO_EXTENSIONS,
        "text": ALLOWED_TEXT_EXTENSIONS,
    }.get(kind)
    if extensions is None:
        raise ValueError(f"Unsupported browse kind: {kind}")
    if not path:
        if os.name == "nt":
            return {"path": "", "parent": None, "entries": _windows_drives()}
        path = "/"

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    if not p.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    dirs: list[dict] = []
    files: list[dict] = []
    try:
        for entry in p.iterdir():
            try:
                if entry.is_dir():
                    dirs.append({"name": entry.name, "path": str(entry), "is_dir": True})
                elif entry.suffix.lower() in extensions:
                    files.append({"name": entry.name, "path": str(entry), "is_dir": False})
            except OSError:
                continue  # inaccessible entry (permissions, broken symlink, etc.)
    except OSError as exc:
        raise PermissionError(f"Cannot list directory: {path}") from exc

    dirs.sort(key=lambda e: e["name"].lower())
    files.sort(key=lambda e: e["name"].lower())

    # A drive root's parent is itself - treat that as "back to the drive list".
    parent = str(p.parent) if p.parent != p else None
    return {"path": str(p), "parent": parent, "entries": dirs + files}
