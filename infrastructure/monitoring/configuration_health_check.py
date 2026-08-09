"""
===============================================================================
BHASHA MITRA
===============================================================================

Module:
    configuration_health_check.py

Layer:
    Infrastructure / Monitoring

Description:
    Performs health verification for the application configuration.

Responsibilities:
    - Check application configuration availability
    - Verify mandatory settings exist
    - Verify configuration source is accessible
    - Return configuration health status

Does Not:
    - Persist health results
    - Check storage accessibility
    - Check worker health
    - Check AI provider health

===============================================================================
"""

from __future__ import annotations

from app.application.dto.health_response import (
    ComponentHealth,
)

from infrastructure.configuration.configuration_manager import (
    ConfigurationManager,
)


class ConfigurationHealthCheck:
    """
    Checks the health of the application configuration.
    """

    def __init__(
        self,
        configuration_manager: ConfigurationManager | None = None,
    ) -> None:

        self._configuration = (
            configuration_manager
            or ConfigurationManager()
        )

    async def check(
        self,
    ) -> ComponentHealth:
        """
        Execute the configuration health check.
        """

        if not self._configuration.is_configuration_source_accessible():

            return ComponentHealth(
                name="configuration",
                status="DOWN",
                message=(
                    "Configuration source is not accessible."
                ),
            )

        if not self._configuration.is_application_configured():

            return ComponentHealth(
                name="configuration",
                status="DOWN",
                message=(
                    "Application configuration is incomplete."
                ),
                details={
                    "required": (
                        "output_path,database_path"
                    ),
                },
            )

        return ComponentHealth(
            name="configuration",
            status="UP",
            message=(
                "Configuration loaded successfully."
            ),
        )