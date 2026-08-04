"""
Disk Usage Utility.

Provides helper methods for calculating storage usage and file counts.
"""

from __future__ import annotations

from pathlib import Path


class DiskUsage:
    """
    Utility for calculating filesystem usage statistics.
    """

    @staticmethod
    def directory_size(directory: Path) -> int:
        """
        Return total size of all files in bytes.
        """

        if not directory.exists():
            return 0

        total = 0

        for file in directory.rglob("*"):

            if file.is_file():
                total += file.stat().st_size

        return total

    @staticmethod
    def file_count(directory: Path) -> int:
        """
        Return number of files.
        """

        if not directory.exists():
            return 0

        return sum(
            1
            for file in directory.rglob("*")
            if file.is_file()
        )

    @staticmethod
    def directory_statistics(
        directory: Path,
    ) -> dict[str, int]:
        """
        Return statistics for one directory.
        """

        return {
            "size": DiskUsage.directory_size(directory),
            "files": DiskUsage.file_count(directory),
        }

    @staticmethod
    def storage_statistics(
        directories: dict[str, Path],
    ) -> dict[str, dict[str, int] | int]:
        """
        Calculate statistics for multiple storage directories.

        Example
        -------
        {
            "uploads": {
                "size": 1048576,
                "files": 12
            },
            "output": {
                "size": 5242880,
                "files": 4
            },
            "total_size": 6291456,
            "total_files": 16
        }
        """

        result: dict[str, dict[str, int] | int] = {}

        total_size = 0
        total_files = 0

        for name, directory in directories.items():

            stats = DiskUsage.directory_statistics(directory)

            result[name] = stats

            total_size += stats["size"]
            total_files += stats["files"]

        result["total_size"] = total_size
        result["total_files"] = total_files

        return result

    @staticmethod
    def format_size(size: int) -> str:
        """
        Convert bytes into a human-readable string.
        """

        units = (
            "B",
            "KB",
            "MB",
            "GB",
            "TB",
        )

        value = float(size)

        for unit in units:

            if value < 1024 or unit == units[-1]:
                return f"{value:.2f} {unit}"

            value /= 1024