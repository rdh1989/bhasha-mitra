"""
===============================================================================
Bhasha Mitra - Application Launcher
===============================================================================
"""

from pathlib import Path
import os
import sys
import threading
import time
import webbrowser

import uvicorn

from app.main import app


APPLICATION_URL = "http://127.0.0.1:8000/"


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


def open_browser_when_ready(server: uvicorn.Server) -> None:
    """Open the packaged application after Uvicorn starts listening."""

    while not server.started and not server.should_exit:
        time.sleep(0.1)

    if server.started:
        webbrowser.open(APPLICATION_URL)


if __name__ == "__main__":

    application_root = get_application_root()

    # Ensure relative paths such as config/, models/, etc.
    # resolve from the application directory.
    os.chdir(application_root)

    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
    server = uvicorn.Server(config)

    if getattr(sys, "frozen", False):
        threading.Thread(
            target=open_browser_when_ready,
            args=(server,),
            name="BhashaMitraBrowserLauncher",
            daemon=True,
        ).start()

    server.run()