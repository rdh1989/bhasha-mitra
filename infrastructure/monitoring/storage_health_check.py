"""
===============================================================================
BHASHA MITRA
===============================================================================

Module:
    storage_health_check.py

Layer:
    Infrastructure / Monitoring

Description:
    Performs health verification for the application storage subsystem.

Responsibilities:
    - Check storage subsystem availability
    - Check configured output and database paths
    - Check storage write access
    - Return storage health status

Does Not:
    - Persist health results
    - Manage storage paths
    - Create fallback storage locations
    - Delete storage files
    - Manage translation jobs

===============================================================================
"""

from __future__ import annotations

from app.application.dto.health_response import (
    ComponentHealth,
)

from infrastructure.filesystem.path_manager import (
    PathManager,
)


class StorageHealthCheck:
    """
    Checks the health of the storage subsystem.
    """

    def __init__(
        self,
        path_manager: PathManager | None = None,
    ) -> None:

        self._paths = (
            path_manager
            or PathManager()
        )

    async def check(
        self,
    ) -> ComponentHealth:
        """
        Execute the storage health check.
        """

        try:

            self._paths.validate()

        except (RuntimeError, OSError) as exc:

            return ComponentHealth(
                name="storage",
                status="DOWN",
                message=str(exc),
            )

        return ComponentHealth(
            name="storage",
            status="UP",
            message="Storage subsystem is operational.",
        )