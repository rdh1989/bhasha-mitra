import threading
import webbrowser
import uvicorn

from launcher import app


def open_browser():
    webbrowser.open("http://127.0.0.1:8000")


if __name__ == "__main__":

    threading.Timer(
        2,
        open_browser
    ).start()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000
    )