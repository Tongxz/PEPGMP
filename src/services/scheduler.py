"""
Detection Scheduler

This module provides a scheduler that decides where and how to run a
detection process. It decouples the API layer from the execution layer.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.services.executors.base import AbstractProcessExecutor
from src.services.executors.local import LocalProcessExecutor


class DetectionScheduler:
    """Schedules detection tasks to appropriate executors."""

    def __init__(self, executor: AbstractProcessExecutor):
        """
        Initializes the scheduler with a specific executor.

        Args:
            executor: An object that conforms to the AbstractProcessExecutor interface.
        """
        self.executor = executor

    def start_detection(self, camera_id: str) -> Dict[str, Any]:
        """Schedules the start of a detection process."""
        # In the future, this method could contain logic to select
        # different executors based on load or camera configuration.
        return self.executor.start(camera_id)

    def stop_detection(self, camera_id: str) -> Dict[str, Any]:
        """Schedules the stop of a detection process."""
        return self.executor.stop(camera_id)

    def restart_detection(self, camera_id: str) -> Dict[str, Any]:
        """Schedules the restart of a detection process."""
        return self.executor.restart(camera_id)

    def get_status(self, camera_id: str) -> Dict[str, Any]:
        """Gets the status of a scheduled process."""
        return self.executor.status(camera_id)

    def status(self, camera_id: str) -> Dict[str, Any]:
        """Alias for get_status for backward compatibility."""
        return self.get_status(camera_id)

    def get_batch_status(self, camera_ids: list[str] | None = None) -> dict[str, Any]:
        """Gets the status for a batch of cameras."""
        # This logic currently resides in the router, but could be moved here.
        # For now, we assume the executor can handle it if needed.
        # This is a placeholder for future refactoring.
        if hasattr(self.executor, "batch_status"):
            return self.executor.batch_status(camera_ids)

        # Fallback to iterating if batch_status is not on executor
        results = {}
        if camera_ids is None:
            # In a full implementation, the scheduler would know about all cameras
            # For now, we rely on the executor to have this info.
            if hasattr(self.executor, "list_cameras"):
                camera_ids = [str(c.get("id")) for c in self.executor.list_cameras()]
            else:
                camera_ids = []

        for cam_id in camera_ids:
            results[cam_id] = self.get_status(cam_id)
        return results

    def stop_all_detections(self) -> Dict[str, Any]:
        """Schedules the stop of all detection processes."""
        return self.executor.stop_all()


# --- Singleton Pattern --- #
_scheduler: Optional[DetectionScheduler] = None


def get_scheduler() -> DetectionScheduler:
    """
    Returns a singleton instance of the DetectionScheduler.

    For the current single-server deployment, it is configured with a
    LocalProcessExecutor.
    """
    global _scheduler
    if _scheduler is None:
        # In a real app, config might be passed here to select the executor
        local_executor = LocalProcessExecutor()
        _scheduler = DetectionScheduler(executor=local_executor)
    return _scheduler
