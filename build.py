"""Builds BhashMitra.exe with PyInstaller.

    .venv\\Scripts\\python.exe build.py

Bundles the FastAPI app, launcher.py (entry point) and their Python
dependencies, plus the small code-adjacent assets (app/static,
app/templates, app/_stubs) into dist/BhashMitra/. It does NOT bundle the
large local asset directories - models/, data/, outputs/, logs/, uploads/ -
those must be copied (or left in place, if building next to this repo) so
they sit right next to the built BhashMitra.exe, same layout as when running
from source. app/config.py resolves them relative to the exe's own folder
when frozen.

Double-clicking dist/BhashMitra/BhashMitra.exe starts the server and opens
it in your default browser automatically (see launcher.py).

Uses --onedir (a folder containing BhashMitra.exe) rather than --onefile:
with torch/transformers/faster-whisper on board, a onefile exe would have to
re-extract a very large payload to a temp folder on every single launch,
which is slow - --onedir only pays that cost once, at build time.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from app.config import APP_NAME, APP_VERSION

ROOT = Path(__file__).resolve().parent
PACKAGE_NAME = "BhashMitra"
SEP = ";" if sys.platform == "win32" else ":"

# torch's own wheel does NOT bundle these itself - a machine without the
# Microsoft Visual C++ Redistributable installed fails to load c10.dll with
# "OSError: [WinError 1114] A dynamic link library (DLL) initialization
# routine failed", even though c10.dll was found fine. Bundled app-local
# below (Microsoft's own supported redistribution method) so the built exe
# never depends on anything being pre-installed on the target machine.
VC_RUNTIME_DLLS = ["vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll", "msvcp140_1.dll", "vcomp140.dll"]

# Packages that ship compiled binaries and/or data files (native DLLs,
# tokenizer/vocab data, espeak-ng data, etc.) that PyInstaller's default
# import-following analysis won't discover on its own - collect each one
# fully (submodules + data files + dynamic libs).
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


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller not found - installing it...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)


def _icon_args() -> list[str]:
    """Best-effort: convert app/static/logo.png to a .ico for the exe icon if
    Pillow happens to be installed. Skipped (default PyInstaller icon) otherwise."""
    logo = ROOT / "app" / "static" / "logo.png"
    if not logo.exists():
        return []
    try:
        from PIL import Image
    except ImportError:
        return []
    ico_path = ROOT / "build" / "bhashmitra.ico"
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        Image.open(logo).convert("RGBA").save(
            ico_path, sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)]
        )
    except Exception:
        return []
    return ["--icon", str(ico_path)]


def _vc_runtime_binary_args() -> list[str]:
    """Copy the MSVC runtime DLLs from this build machine's System32 into
    both the app root and torch/lib (c10.dll's own directory - Windows
    resolves a DLL's dependencies from either location), so they ship
    app-local instead of relying on the target machine having them."""
    system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    args: list[str] = []
    missing = []
    for name in VC_RUNTIME_DLLS:
        src = system32 / name
        if not src.exists():
            missing.append(name)
            continue
        args += ["--add-binary", f"{src}{SEP}."]
        args += ["--add-binary", f"{src}{SEP}torch/lib"]
    if missing:
        print(
            f"WARNING: could not find {missing} under {system32} - the built exe "
            "may still require the VC++ Redistributable on some machines."
        )
    return args


def _build_date() -> str:
    return datetime.now().strftime("%d%m%Y")


def _build_metadata_runtime_hook(build_value: str) -> Path:
    hook_path = ROOT / "build" / "pyi_app_build.py"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    hook_path.write_text(
        "import os\n"
        f"os.environ['BHASHAMITRA_APP_BUILD'] = {build_value!r}\n",
        encoding="utf-8",
    )
    return hook_path


def main() -> None:
    _ensure_pyinstaller()
    build_value = _build_date()
    runtime_hook = _build_metadata_runtime_hook(build_value)

    print(APP_NAME)
    print(f"Version: {APP_VERSION}")
    print(f"Build: {build_value}")
    print()

    args = [
        "--name", PACKAGE_NAME,
        "--onedir",
        "--console",  # keep the console visible so startup/model-load progress and errors are seen
        "--noconfirm",
        "--clean",
        "--specpath", str(ROOT / "build"),
        "--runtime-hook", str(runtime_hook),
        "--add-data", f"{ROOT / 'app' / 'static'}{SEP}app/static",
        "--add-data", f"{ROOT / 'app' / 'templates'}{SEP}app/templates",
        "--add-data", f"{ROOT / 'app' / '_stubs'}{SEP}app/_stubs",
    ]
    for pkg in COLLECT_ALL:
        args += ["--collect-all", pkg]
    args += _icon_args()
    args += _vc_runtime_binary_args()
    args.append(str(ROOT / "launcher.py"))

    print("Running PyInstaller with:", " ".join(args))
    import PyInstaller.__main__

    PyInstaller.__main__.run(args)

    exe_path = ROOT / "dist" / PACKAGE_NAME / f"{PACKAGE_NAME}.exe"
    print()
    print(f"Build complete: {exe_path}")
    print(
        "Before running it, copy these folders (unchanged) from this repo "
        f"into {exe_path.parent} so the app can find its models and keep "
        "its data: models/, data/, outputs/, logs/, uploads/."
    )


if __name__ == "__main__":
    main()
