"""Build the Windows application and stage its external AI models."""

from __future__ import annotations

import filecmp
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = PROJECT_ROOT / "Bhasha-Mitra.spec"
MODELS_SOURCE = PROJECT_ROOT.parent / "models"
APPLICATION_DIRECTORY = PROJECT_ROOT / "dist" / "Bhasha-Mitra"
VC_RUNTIME_FILES = (
	"msvcp140.dll",
	"MSVCP140_1.dll",
	"MSVCP140_ATOMIC_WAIT.dll",
	"vcruntime140.dll",
	"vcruntime140_1.dll",
)


def _normalize_vc_runtime() -> None:
	system_directory = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
	runtime_directory = APPLICATION_DIRECTORY / "_internal"

	for file_name in VC_RUNTIME_FILES:
		source = system_directory / file_name
		destination = runtime_directory / file_name
		if not source.is_file():
			raise FileNotFoundError(
				f"Microsoft Visual C++ runtime not found: {source}"
			)
		if destination.is_file() and filecmp.cmp(source, destination, shallow=False):
			continue
		shutil.copy2(source, destination)


def main() -> None:
	if sys.version_info[:2] != (3, 12):
		raise RuntimeError(
			"Bhasha Mitra must be built with Python 3.12; "
			f"current interpreter is {sys.version.split()[0]}."
		)

	if not MODELS_SOURCE.is_dir():
		raise FileNotFoundError(
			f"Model directory not found: {MODELS_SOURCE}"
		)

	subprocess.run(
		[
			sys.executable,
			"-m",
			"PyInstaller",
			"--noconfirm",
			"--clean",
			str(SPEC_PATH),
		],
		cwd=PROJECT_ROOT,
		check=True,
	)

	_normalize_vc_runtime()

	models_destination = APPLICATION_DIRECTORY / "models"
	print(f"Staging models: {MODELS_SOURCE} -> {models_destination}")
	shutil.copytree(
		MODELS_SOURCE,
		models_destination,
		dirs_exist_ok=True,
	)

	print(f"Build complete: {APPLICATION_DIRECTORY}")


if __name__ == "__main__":
	main()
