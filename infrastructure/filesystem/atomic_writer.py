"""
Atomic File Writer.

Ensures files are written safely by first writing to a temporary
file and then replacing the destination atomically.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


class AtomicWriter:
    """
    Utility for atomic file writes.
    """

    @staticmethod
    def write_text(
        destination: Path,
        content: str,
        encoding: str = "utf-8",
    ) -> None:
        """
        Atomically write text to a file.
        """

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            delete=False,
            dir=destination.parent,
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        os.replace(
            temp_path,
            destination,
        )

    @staticmethod
    def write_bytes(
        destination: Path,
        content: bytes,
    ) -> None:
        """
        Atomically write binary data.
        """

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=destination.parent,
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        os.replace(
            temp_path,
            destination,
        )

    @staticmethod
    def copy_file(
        source: Path,
        destination: Path,
        chunk_size: int = 1024 * 1024,
    ) -> None:
        """
        Atomically copy a file.
        """

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=destination.parent,
        ) as temp_file:

            with source.open("rb") as src:

                while True:
                    chunk = src.read(chunk_size)

                    if not chunk:
                        break

                    temp_file.write(chunk)

            temp_path = Path(temp_file.name)

        os.replace(
            temp_path,
            destination,
        )

    @staticmethod
    def write_stream(
        stream,
        destination: Path,
        chunk_size: int = 1024 * 1024,
    ) -> None:
        """
        Atomically write from a binary stream.
        """

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=destination.parent,
        ) as temp_file:

            while True:

                chunk = stream.read(chunk_size)

                if not chunk:
                    break

                temp_file.write(chunk)

            temp_path = Path(temp_file.name)

        os.replace(
            temp_path,
            destination,
        )