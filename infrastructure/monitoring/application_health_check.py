"""
Application Health Check

Performs health verification for the core application.
"""

from __future__ import annotations

from app.application.dto.health_response import ComponentHealth


class ApplicationHealthCheck:
    """
    Checks the health of the running application.
    """

    async def check(self) -> ComponentHealth:
        """
        Execute the application health check.
        """

        return ComponentHealth(
            name="application",
            status="UP",
            message="Application is running.",
        )