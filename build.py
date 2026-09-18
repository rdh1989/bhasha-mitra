"""
===============================================================================
Bhasha Mitra - PyInstaller Build Script
===============================================================================

File        : build.py
Application : Bhasha Mitra
Purpose     : Build the BhashaMitra Windows application using PyInstaller.

Usage
-----
    .venv\\Scripts\\python.exe build.py

Build Output
------------
Each build is isolated under a date-specific directory using the current
date in DDMMYYYY format. The PyInstaller onedir output is written directly
under that directory (no intermediate build/ or dist/ directories remain in
the final release):

    releases/
    └── DDMMYYYY/
        ├── BhashMitra/
        │   ├── BhashMitra.exe
        │   └── ...
        ├── RELEASE_NOTES.md
        └── BUILD_METADATA.json

Example for 18 September 2026:

    releases/
    └── 18092026/
        ├── BhashMitra/
        │   └── BhashMitra.exe
        ├── RELEASE_NOTES.md
        └── BUILD_METADATA.json

PyInstaller still requires a work directory for its intermediate artifacts
(spec file, generated icon, runtime hook, etc.). This temporary workspace is
created under releases/DDMMYYYY/_build/ and is deleted automatically once
the build succeeds and BhashMitra.exe has been verified. If the build fails,
_build/ is kept so the failure can be investigated.

The large runtime asset directories are intentionally NOT bundled by
PyInstaller:

    models/
    data/
    outputs/
    logs/
    uploads/

These directories must be copied or kept alongside the built application
according to the path-resolution behavior defined in app/config.py.

Packaging Strategy
------------------
PyInstaller --onedir is used instead of --onefile.

The application contains large AI dependencies such as PyTorch,
Transformers, Faster-Whisper, ONNX Runtime and Piper. Using --onefile would
require the complete packaged payload to be extracted to a temporary
directory every time the application starts.

Using --onedir avoids this repeated extraction cost.

Build Metadata
--------------
Application version is read from app.config.

The build date is generated automatically when this script runs and is also
used as the release directory name.

Example:

    Version : 1.1.0
    Build   : 18092026

The build value is injected into the frozen application through a temporary
PyInstaller runtime hook generated under releases/DDMMYYYY/_build.

Application Entry Point
-----------------------
launcher.py

Final Executable
----------------
releases/DDMMYYYY/BhashMitra/BhashMitra.exe

Release Metadata
----------------
On a successful build, two additional files are generated alongside the
application directory:

    releases/DDMMYYYY/BUILD_METADATA.json
    releases/DDMMYYYY/RELEASE_NOTES.md

Important
---------
The releases directory contains generated build/release artifacts and should
normally be excluded from Git source control.

===============================================================================
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from app.config import APP_NAME, APP_VERSION


# =============================================================================
# Project / Build Configuration
# =============================================================================

ROOT = Path(__file__).resolve().parent

PACKAGE_NAME = "BhashMitra"

SEP = ";" if sys.platform == "win32" else ":"


# =============================================================================
# Build Date / Release Directory
# =============================================================================

def _build_date() -> str:
    """Return the current build date in DDMMYYYY format."""

    return datetime.now().strftime("%d%m%Y")


BUILD_VALUE = _build_date()

# Every build run gets its own date-specific directory. The final
# application (BhashMitra/BhashMitra.exe) lives directly under this
# directory - there is no intermediate build/ or dist/ directory.
RELEASES_DIR = ROOT / "releases" / BUILD_VALUE

# Temporary PyInstaller work area (spec file, generated icon, runtime hook,
# etc.). Removed automatically after a successful, verified build.
BUILD_DIR = RELEASES_DIR / "_build"

# PyInstaller writes its --onedir output directly here, producing
# releases/DDMMYYYY/BhashMitra/ instead of releases/DDMMYYYY/dist/BhashMitra/.
DIST_DIR = RELEASES_DIR


# =============================================================================
# Microsoft Visual C++ Runtime DLLs
# =============================================================================

VC_RUNTIME_DLLS = [
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "msvcp140.dll",
    "msvcp140_1.dll",
    "vcomp140.dll",
]


# =============================================================================
# Packages Requiring Complete Collection
# =============================================================================

COLLECT_ALL = [
    "torch",
    "torchaudio",
    "transformers",
    "tokenizers",
    "sentencepiece",
    "safetensors",
    "huggingface_hub",
    "faster_whisper",
    "ctranslate2",
    "onnxruntime",
    "piper",
    "soundfile",
    "imageio_ffmpeg",
    "IndicTransToolkit",
    "indicnlp",
]


# =============================================================================
# Helper Functions
# =============================================================================

def _ensure_pyinstaller() -> None:
    """Ensure PyInstaller is installed in the active Python environment."""

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller not found - installing it...")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "pyinstaller",
            ],
            check=True,
        )


def _icon_args() -> list[str]:
    """
    Best-effort conversion of the application PNG logo to ICO format.

    The generated ICO file is stored under the current release build
    directory.
    """

    logo = ROOT / "app" / "static" / "logo.png"

    if not logo.exists():
        return []

    try:
        from PIL import Image
    except ImportError:
        return []

    ico_path = BUILD_DIR / "bhashmitra.ico"
    ico_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        Image.open(logo).convert("RGBA").save(
            ico_path,
            sizes=[
                (256, 256),
                (128, 128),
                (64, 64),
                (32, 32),
                (16, 16),
            ],
        )
    except Exception:
        return []

    return [
        "--icon",
        str(ico_path),
    ]


def _vc_runtime_binary_args() -> list[str]:
    """
    Copy Microsoft Visual C++ runtime DLLs into the application bundle.

    DLLs are copied both to the application root and to torch/lib so that
    the packaged application does not depend on the target machine having
    the VC++ Redistributable installed separately.
    """

    system32 = (
        Path(os.environ.get("SystemRoot", r"C:\Windows"))
        / "System32"
    )

    args: list[str] = []
    missing: list[str] = []

    for name in VC_RUNTIME_DLLS:
        src = system32 / name

        if not src.exists():
            missing.append(name)
            continue

        args += [
            "--add-binary",
            f"{src}{SEP}.",
        ]

        args += [
            "--add-binary",
            f"{src}{SEP}torch/lib",
        ]

    if missing:
        print(
            f"WARNING: could not find {missing} under {system32}. "
            "The built application may still require the VC++ "
            "Redistributable on some machines."
        )

    return args


def _build_metadata_runtime_hook(build_value: str) -> Path:
    """
    Generate a temporary PyInstaller runtime hook containing build metadata.

    The generated hook is stored under the current release build directory.
    """

    hook_path = BUILD_DIR / "pyi_app_build.py"

    hook_path.parent.mkdir(parents=True, exist_ok=True)

    hook_path.write_text(
        "import os\n"
        f"os.environ['BHASHAMITRA_APP_BUILD'] = {build_value!r}\n",
        encoding="utf-8",
    )

    return hook_path


def _write_build_metadata() -> Path:
    """Write BUILD_METADATA.json describing this release."""

    metadata = {
        "application": APP_NAME,
        "version": APP_VERSION,
        "build": BUILD_VALUE,
        "build_date": datetime.now().strftime("%Y-%m-%d"),
        "packaging": "onedir",
        "entry_point": "launcher.py",
        "executable": f"{PACKAGE_NAME}/{PACKAGE_NAME}.exe",
    }

    metadata_path = RELEASES_DIR / "BUILD_METADATA.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=4) + "\n",
        encoding="utf-8",
    )

    return metadata_path


def _write_release_notes() -> Path:
    """Write RELEASE_NOTES.md describing this release."""

    build_date = datetime.now().strftime("%Y-%m-%d")

    content = (
        "# Bhasha Mitra Release Notes\n"
        "\n"
        "## Release Information\n"
        "\n"
        f"- Application: {APP_NAME}\n"
        f"- Version: {APP_VERSION}\n"
        f"- Build: {BUILD_VALUE}\n"
        f"- Build Date: {build_date}\n"
        "- Packaging: onedir\n"
        f"- Executable: {PACKAGE_NAME}/{PACKAGE_NAME}.exe\n"
        "\n"
        "## Changes\n"
        "\n"
        "- Add release-specific changes here.\n"
        "- Add bug fixes, enhancements, model changes, UI changes, and other\n"
        "  user-visible changes for this build.\n"
        "\n"
        "## Build Artifact\n"
        "\n"
        f"    {PACKAGE_NAME}/{PACKAGE_NAME}.exe\n"
        "\n"
        "## Runtime Assets\n"
        "\n"
        "These directories remain outside the PyInstaller bundle and must be\n"
        "copied or kept alongside the built application:\n"
        "\n"
        "- models/\n"
        "- data/\n"
        "- outputs/\n"
        "- logs/\n"
        "- uploads/\n"
    )

    notes_path = RELEASES_DIR / "RELEASE_NOTES.md"
    notes_path.write_text(content, encoding="utf-8")

    return notes_path


def _print_build_failed() -> None:
    print()
    print("=" * 60)
    print("BUILD FAILED")
    print("=" * 60)
    print(f"Temporary build files preserved for inspection at: {BUILD_DIR}")
    print("=" * 60)


# =============================================================================
# Main Build Process
# =============================================================================

def main() -> None:
    """Build BhashMitra.exe using PyInstaller."""

    _ensure_pyinstaller()

    # Ensure the release directory and temporary build workspace exist.
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Generate the build metadata runtime hook.
    runtime_hook = _build_metadata_runtime_hook(BUILD_VALUE)

    print()
    print("=" * 60)
    print(f"{APP_NAME}")
    print(f"Version : {APP_VERSION}")
    print(f"Build   : {BUILD_VALUE}")
    print(f"Output  : {RELEASES_DIR}")
    print("=" * 60)
    print()

    args = [
        "--name",
        PACKAGE_NAME,

        # Directory-based packaging for the AI-heavy application.
        "--onedir",

        # Keep console visible for startup, model-loading progress and errors.
        "--console",

        "--noconfirm",
        "--clean",

        # -----------------------------------------------------------------
        # PyInstaller generated artifacts
        # -----------------------------------------------------------------

        "--workpath",
        str(BUILD_DIR),

        "--distpath",
        str(DIST_DIR),

        "--specpath",
        str(BUILD_DIR),

        # -----------------------------------------------------------------
        # Application build metadata
        # -----------------------------------------------------------------

        "--runtime-hook",
        str(runtime_hook),

        # -----------------------------------------------------------------
        # Application assets
        # -----------------------------------------------------------------

        "--add-data",
        f"{ROOT / 'app' / 'static'}{SEP}app/static",

        "--add-data",
        f"{ROOT / 'app' / 'templates'}{SEP}app/templates",

        "--add-data",
        f"{ROOT / 'app' / '_stubs'}{SEP}app/_stubs",
    ]

    # ---------------------------------------------------------------------
    # Collect packages containing native binaries, dynamic libraries,
    # tokenizer/vocabulary files or other package data.
    # ---------------------------------------------------------------------

    for pkg in COLLECT_ALL:
        args += [
            "--collect-all",
            pkg,
        ]

    # Application icon.
    args += _icon_args()

    # Microsoft Visual C++ runtime dependencies.
    args += _vc_runtime_binary_args()

    # Application entry point.
    args.append(
        str(ROOT / "launcher.py")
    )

    print("Running PyInstaller with:")
    print(" ".join(args))
    print()

    import PyInstaller.__main__

    try:
        PyInstaller.__main__.run(args)
    except SystemExit as exc:
        if exc.code not in (0, None):
            _print_build_failed()
            raise
    except BaseException:
        _print_build_failed()
        raise

    # ---------------------------------------------------------------------
    # Final executable
    # ---------------------------------------------------------------------

    exe_path = (
        DIST_DIR
        / PACKAGE_NAME
        / f"{PACKAGE_NAME}.exe"
    )

    if not exe_path.exists():
        _print_build_failed()
        raise RuntimeError(
            "PyInstaller build did not produce the expected executable: "
            f"{exe_path}"
        )

    # The executable has been verified - generate the release metadata/notes
    # and remove the temporary PyInstaller work directory.
    metadata_path = _write_build_metadata()
    notes_path = _write_release_notes()

    shutil.rmtree(BUILD_DIR, ignore_errors=True)

    print()
    print("=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    print(f"Application : {APP_NAME}")
    print(f"Version     : {APP_VERSION}")
    print(f"Build       : {BUILD_VALUE}")
    print(f"EXE         : {exe_path}")
    print(f"Metadata    : {metadata_path}")
    print(f"Notes       : {notes_path}")
    print()
    print(
        "Before running the packaged application, ensure these folders "
        "are available according to app/config.py:"
    )
    print("    models/")
    print("    data/")
    print("    outputs/")
    print("    logs/")
    print("    uploads/")
    print("=" * 60)


if __name__ == "__main__":
    main()
