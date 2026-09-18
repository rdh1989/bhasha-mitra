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
date in DDMMYYYY format:

    releases/
    └── DDMMYYYY/
        ├── build/
        │   ├── BhashMitra/
        │   ├── bhashmitra.ico
        │   ├── pyi_app_build.py
        │   └── ...
        │
        └── dist/
            └── BhashMitra/
                ├── BhashMitra.exe
                └── ...

Example for 18 September 2026:

    releases/
    └── 18092026/
        ├── build/
        └── dist/
            └── BhashMitra/
                └── BhashMitra.exe

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
PyInstaller runtime hook generated under releases/DDMMYYYY/build.

Application Entry Point
-----------------------
launcher.py

Final Executable
----------------
releases/DDMMYYYY/dist/BhashMitra/BhashMitra.exe

Important
---------
The releases directory contains generated build/release artifacts and should
normally be excluded from Git source control.

===============================================================================
"""

from __future__ import annotations

import os
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

# Every build run gets its own date-specific directory.
RELEASES_DIR = ROOT / "releases" / BUILD_VALUE

BUILD_DIR = RELEASES_DIR / "build"
DIST_DIR = RELEASES_DIR / "dist"


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


# =============================================================================
# Main Build Process
# =============================================================================

def main() -> None:
    """Build BhashMitra.exe using PyInstaller."""

    _ensure_pyinstaller()

    # Ensure the current release build directory exists.
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

    PyInstaller.__main__.run(args)

    # ---------------------------------------------------------------------
    # Final executable
    # ---------------------------------------------------------------------

    exe_path = (
        DIST_DIR
        / PACKAGE_NAME
        / f"{PACKAGE_NAME}.exe"
    )

    print()
    print("=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    print(f"Application : {APP_NAME}")
    print(f"Version     : {APP_VERSION}")
    print(f"Build       : {BUILD_VALUE}")
    print(f"EXE         : {exe_path}")
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
