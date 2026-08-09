# """
# ===============================================================================
# BHASHA MITRA
# Worker Registration
# ===============================================================================

# Module:
#     worker_registration.py

# Layer:
#     Infrastructure / Bootstrap

# Description:
#     Registers all application background workers with WorkerManager.

# Responsibilities:
#     - Register container-created workers
#     - Register maintenance workers
#     - Keep dependency wiring inside ApplicationContainer
#     - Provide a single worker registration point

# Business logic must not live here.
# """

# from __future__ import annotations

# from infrastructure.bootstrap.application_container import (
#     ApplicationContainer,
# )

# from workers.cleanup_worker import CleanupWorker
# from workers.monitoring_worker import MonitoringWorker
# from workers.retry_worker import RetryWorker
# from workers.worker_manager import WorkerManager


# def register_workers(
#     manager: WorkerManager,
#     container: ApplicationContainer,
# ) -> None:
#     """
#     Register all application background workers.
#     """

#     # =========================================================================
#     # Core processing workers
#     # =========================================================================

#     manager.register(
#         container.preprocessing_worker
#     )

#     manager.register(
#         container.translation_worker
#     )

#     # =========================================================================
#     # Maintenance workers
#     # =========================================================================

#     manager.register(
#         CleanupWorker()
#     )

#     manager.register(
#         RetryWorker(
#             container.translation_queue
#         )
#     )

#     manager.register(
#         MonitoringWorker()
#     )


"""
Module:
worker_registration.py

Layer:
Infrastructure / Bootstrap

Description:
Registers all application background workers with WorkerManager.

Responsibilities:
- Register container-created workers
- Register maintenance workers
- Keep dependency wiring inside ApplicationContainer
- Provide a single worker registration point

Business logic must not live here.
"""

from __future__ import annotations

from infrastructure.bootstrap.application_container import (
    ApplicationContainer,
)

from workers.cleanup_worker import CleanupWorker
from workers.monitoring_worker import MonitoringWorker
from workers.retry_worker import RetryWorker
from workers.worker_manager import WorkerManager


def register_workers(
    manager: WorkerManager,
    container: ApplicationContainer,
) -> None:
    """
    Register all application background workers.
    """

    # =========================================================================
    # Core processing workers
    # =========================================================================

    manager.register(
        container.preprocessing_worker
    )

    manager.register(
        container.translation_worker
    )

    # Dubbing worker added to the core processing pipeline.
    manager.register(
        container.dubbing_worker
    )

    # =========================================================================
    # Maintenance workers
    # =========================================================================

    manager.register(
        CleanupWorker()
    )

    manager.register(
        RetryWorker(
            container.translation_queue
        )
    )

    manager.register(
        MonitoringWorker()
    )