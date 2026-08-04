"""
Application Health Service

Provides aggregated health information for the application.
"""

from datetime import datetime, timezone
from time import monotonic

from app.application.dto.health_response import (
    ComponentHealth,
    HealthResponse,
)


class HealthService:
    """
    Application service responsible for collecting
    system health information.
    """

    _started_at = monotonic()

    def __init__(self, version: str = "1.0.0") -> None:
        self._version = version

    async def get_health(self) -> HealthResponse:
        """
        Returns the current application health.
        """

        uptime = monotonic() - self._started_at

        return HealthResponse(
            status="UP",
            version=self._version,
            uptime_seconds=uptime,
            timestamp=datetime.now(timezone.utc).isoformat(),
            components=[
                ComponentHealth(
                    name="application",
                    status="UP",
                    message="Application is running.",
                )
            ],
        )