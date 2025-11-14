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

    def start_detection(
        self, camera_id: str, camera_config: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Schedules the start of a detection process.

        Args:
            camera_id: The ID of the camera to start.
            camera_config: Optional camera configuration dictionary.
                          If provided, will be passed to the executor.
        """
        # In the future, this method could contain logic to select
        # different executors based on load or camera configuration.
        return self.executor.start(camera_id, camera_config)

    def stop_detection(self, camera_id: str) -> Dict[str, Any]:
        """Schedules the stop of a detection process."""
        return self.executor.stop(camera_id)

    def restart_detection(
        self, camera_id: str, camera_config: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Schedules the restart of a detection process.

        Args:
            camera_id: The ID of the camera to restart.
            camera_config: Optional camera configuration dictionary.
                          If provided, will be passed to the executor.
        """
        return self.executor.restart(camera_id, camera_config)

    def get_status(self, camera_id: str) -> Dict[str, Any]:
        """Gets the status of a scheduled process."""
        return self.executor.status(camera_id)

    def status(self, camera_id: str) -> Dict[str, Any]:
        """Alias for get_status for backward compatibility."""
        return self.get_status(camera_id)

    def get_batch_status(self, camera_ids: list[str] | None = None) -> dict[str, Any]:
        """Gets the status for a batch of cameras.

        Args:
            camera_ids: 相机ID列表。如果为None或空列表，返回空字典。
                       注意：在FastAPI环境中，应该由API层从数据库获取相机列表
                       并传递给此方法，而不是让此方法调用executor.list_cameras()。

        Returns:
            包含每个相机状态的字典，键为相机ID
        """
        # 如果executor有batch_status方法，直接使用
        if hasattr(self.executor, "batch_status"):
            return self.executor.batch_status(camera_ids)

        # Fallback to iterating if batch_status is not on executor
        results = {}

        # 如果camera_ids为None或空列表，返回空字典
        # 注意：不再调用executor.list_cameras()，因为这会触发YAML回退警告
        # 在FastAPI环境中，应该由API层从数据库获取相机列表并传递过来
        if not camera_ids:
            # 返回空字典，而不是调用list_cameras()
            # 这样可以避免在FastAPI环境中触发YAML回退警告
            return results

        # 查询指定相机的状态
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
