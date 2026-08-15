"""
===============================================================================
Bhasha Mitra - Application Launcher
===============================================================================
"""

from pathlib import Path
import os
import sys

import uvicorn

from app.main import app


def get_application_root() -> Path:
    """
    Return the application root directory.

    Development:
        Directory containing launcher.py

    Packaged:
        Directory containing Bhasha-Mitra.exe
    """

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


if __name__ == "__main__":

    application_root = get_application_root()

    # Ensure relative paths such as config/, models/, etc.
    # resolve from the application directory.
    os.chdir(application_root)

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
    )