"""
Abstract Base Class for Process Executors.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class AbstractProcessExecutor(ABC):
    """Defines the interface for all process executors."""

    @abstractmethod
    def start(self, camera_id: str) -> Dict[str, Any]:
        """
        Starts a detection process for a given camera ID.

        Args:
            camera_id: The ID of the camera to start.

        Returns:
            A dictionary containing the result of the start operation,
            including process information like PID.
        """

    @abstractmethod
    def stop(self, camera_id: str) -> Dict[str, Any]:
        """
        Stops the detection process for a given camera ID.

        Args:
            camera_id: The ID of the camera to stop.

        Returns:
            A dictionary containing the result of the stop operation.
        """

    @abstractmethod
    def restart(self, camera_id: str) -> Dict[str, Any]:
        """
        Restarts the detection process for a given camera ID.

        Args:
            camera_id: The ID of the camera to restart.

        Returns:
            A dictionary containing the result of the restart operation.
        """

    @abstractmethod
    def status(self, camera_id: str) -> Dict[str, Any]:
        """
        Gets the status of the detection process for a given camera ID.

        Args:
            camera_id: The ID of the camera to check.

        Returns:
            A dictionary containing the process status (e.g., running, pid).
        """

    @abstractmethod
    def stop_all(self) -> Dict[str, Any]:
        """
        Stops all managed detection processes.

        Returns:
            A dictionary summarizing the stop-all operation.
        """
