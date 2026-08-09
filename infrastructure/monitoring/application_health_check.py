"""
===============================================================================
BHASHA MITRA
===============================================================================

Module:
    application_health_check.py

Layer:
    Infrastructure / Monitoring

Description:
    Performs the application-level health check.

Responsibilities:
    - Check application runtime availability
    - Return application health status

Does Not:
    - Persist health results
    - Perform configuration checks
    - Perform storage checks
    - Perform worker checks
    - Perform AI provider checks

===============================================================================
"""

from __future__ import annotations

from app.application.dto.health_response import (
    ComponentHealth,
)


class ApplicationHealthCheck:
    """
    Checks the health of the running application.
    """

    async def check(
        self,
    ) -> ComponentHealth:
        """
        Execute the application health check.
        """

        return ComponentHealth(
            name="application",
            status="UP",
            message="Application is running.",
        )