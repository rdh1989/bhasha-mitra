"""Desktop entry point built into BhashMitra.exe by build.py.

Starts the FastAPI app (same app as `uvicorn app.main:app`) on localhost and
opens it in the default browser once it responds. Not needed when running
from source - use the uvicorn command in README.md for that instead.
"""
from __future__ import annotations

import multiprocessing
import threading
import time
import urllib.request
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000


def _open_browser_when_ready() -> None:
    url = f"http://{HOST}:{PORT}/"
    # Model loading (ASR/translation/TTS) at startup can take anywhere from
    # ~20s to a few minutes depending on the machine - keep polling instead
    # of opening the browser too early.
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(1)
    webbrowser.open(url)


def main() -> None:
    threading.Thread(target=_open_browser_when_ready, daemon=True).start()
    from app.main import app  # imported here so the console window shows load progress first

    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
