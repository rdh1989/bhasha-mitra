from pathlib import Path
import sys
import uvicorn


def get_app_root() -> Path:
    """
    Return the directory containing the packaged application.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


if __name__ == "__main__":
    app_root = get_app_root()

    # Make relative paths resolve from the application directory.
    import os
    os.chdir(app_root)

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )