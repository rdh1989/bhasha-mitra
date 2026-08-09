"""
===============================================================================
BHASHA MITRA
===============================================================================

Module:
    disk_usage.py

Layer:
    Infrastructure / Filesystem

Description:
    Provides filesystem storage usage and file-count statistics.

Responsibilities:
    - Calculate directory size
    - Count files
    - Calculate storage statistics
    - Format byte sizes for display

Does Not:
    - Manage storage paths
    - Define retention policies
    - Delete files

===============================================================================
"""

from __future__ import annotations

from pathlib import Path


class DiskUsage:
    """
    Utility for calculating filesystem usage statistics.
    """

    @staticmethod
    def directory_size(
        directory: Path,
    ) -> int:
        """
        Return total size of all files in bytes.
        """

        directory = Path(directory)

        if not directory.exists():
            return 0

        if not directory.is_dir():

            raise NotADirectoryError(
                f"Not a directory: {directory}"
            )

        total = 0

        for file in directory.rglob("*"):

            if not file.is_file():
                continue

            try:

                total += file.stat().st_size

            except OSError:

                # A file may disappear while the directory
                # is being scanned.
                continue

        return total

    @staticmethod
    def file_count(
        directory: Path,
    ) -> int:
        """
        Return number of files.
        """

        directory = Path(directory)

        if not directory.exists():
            return 0

        if not directory.is_dir():

            raise NotADirectoryError(
                f"Not a directory: {directory}"
            )

        count = 0

        for file in directory.rglob("*"):

            if file.is_file():
                count += 1

        return count

    @staticmethod
    def directory_statistics(
        directory: Path,
    ) -> dict[str, int]:
        """
        Return statistics for one directory.

        Returns:
            {
                "size": <bytes>,
                "files": <count>
            }
        """

        return {
            "size": DiskUsage.directory_size(
                directory
            ),
            "files": DiskUsage.file_count(
                directory
            ),
        }

    @staticmethod
    def storage_statistics(
        directories: dict[str, Path],
    ) -> dict[str, dict[str, int] | int]:
        """
        Calculate statistics for multiple storage directories.

        Example:

            {
                "output": {
                    "size": 5242880,
                    "files": 4
                },
                "cache": {
                    "size": 1048576,
                    "files": 3
                },
                "total_size": 6291456,
                "total_files": 7
            }
        """

        result: dict[
            str,
            dict[str, int] | int,
        ] = {}

        total_size = 0
        total_files = 0

        for name, directory in directories.items():

            stats = (
                DiskUsage.directory_statistics(
                    directory
                )
            )

            result[name] = stats

            total_size += stats["size"]
            total_files += stats["files"]

        result["total_size"] = total_size
        result["total_files"] = total_files

        return result

    @staticmethod
    def format_size(
        size: int,
    ) -> str:
        """
        Convert bytes into a human-readable string.
        """

        if size < 0:

            raise ValueError(
                "Size cannot be negative."
            )

        units = (
            "B",
            "KB",
            "MB",
            "GB",
            "TB",
        )

        value = float(size)

        for unit in units:

            if (
                value < 1024
                or unit == units[-1]
            ):

                return (
                    f"{value:.2f} {unit}"
                )

            value /= 1024

        return f"{value:.2f} TB"