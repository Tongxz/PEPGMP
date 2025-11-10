"""摄像头控制领域服务."""

import logging
from datetime import datetime
from pathlib import Path as FilePath
from typing import Any, Dict, List, Optional

from src.domain.services.camera_service import CameraService

logger = logging.getLogger(__name__)


class CameraControlService:
    """摄像头控制领域服务.

    提供摄像头进程控制相关的业务逻辑，包括启动、停止、状态查询等。
    """

    def __init__(
        self,
        camera_service: CameraService,
        scheduler: Any,  # DetectionScheduler
    ):
        """初始化摄像头控制服务.

        Args:
            camera_service: 摄像头服务（用于CRUD操作）
            scheduler: 检测调度器（用于进程控制）
        """
        self.camera_service = camera_service
        self.scheduler = scheduler

    def start_camera(self, camera_id: str) -> Dict[str, Any]:
        """启动指定摄像头的检测进程.

        业务规则：
        1. 检查摄像头是否已在运行（避免重复启动）
        2. 检查系统资源是否足够
        3. 启动进程
        4. 发布摄像头启动事件（未来实现）

        Args:
            camera_id: 摄像头ID

        Returns:
            包含启动结果的字典

        Raises:
            ValueError: 如果摄像头不存在、已在运行或启动失败
        """
        try:
            # 1. 业务规则：检查摄像头是否已在运行
            status = self.scheduler.get_status(camera_id)
            if status.get("running"):
                pid = status.get("pid", "unknown")
                raise ValueError(f"摄像头 {camera_id} 已在运行（PID: {pid}），" "请先停止后再启动")

            # 2. 业务规则：检查系统资源（简化版，检查运行中的摄像头数量）
            batch_status = self.scheduler.get_batch_status()
            running_count = sum(1 for s in batch_status.values() if s.get("running"))
            MAX_CONCURRENT_CAMERAS = 10  # 可配置

            if running_count >= MAX_CONCURRENT_CAMERAS:
                raise ValueError(
                    f"系统资源不足：当前运行 {running_count} 个摄像头，"
                    f"已达上限 {MAX_CONCURRENT_CAMERAS}"
                )

            # 3. 启动进程（委托给执行器）
            res = self.scheduler.start_detection(camera_id)
            if not res.get("ok"):
                error_msg = res.get("error") or "启动摄像头失败"
                logger.error(f"启动摄像头失败 {camera_id}: {error_msg}")
                raise ValueError(error_msg)

            # 4. 记录成功日志
            logger.info(
                f"✓ 摄像头启动成功 {camera_id}: " f"pid={res.get('pid')}, log={res.get('log')}"
            )

            # TODO: 发布领域事件 CameraStartedEvent

            return res

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"启动摄像头异常 {camera_id}: {e}")
            raise ValueError(f"启动摄像头失败: {e}")

    def stop_camera(self, camera_id: str) -> Dict[str, Any]:
        """停止指定摄像头的检测进程.

        业务规则：
        1. 检查摄像头是否正在运行
        2. 停止进程
        3. 验证进程已停止
        4. 发布摄像头停止事件（未来实现）

        Args:
            camera_id: 摄像头ID

        Returns:
            包含停止结果的字典

        Raises:
            ValueError: 如果停止失败
        """
        try:
            # 1. 业务规则：检查摄像头是否正在运行
            status = self.scheduler.get_status(camera_id)
            if not status.get("running"):
                logger.warning(f"摄像头 {camera_id} 未在运行，无需停止")
                return {
                    "ok": True,
                    "running": False,
                    "message": "摄像头未在运行",
                }

            pid = status.get("pid")
            logger.info(f"正在停止摄像头 {camera_id} (PID: {pid})...")

            # 2. 停止进程（委托给执行器）
            res = self.scheduler.stop_detection(camera_id)
            if not res.get("ok"):
                error_msg = res.get("error") or "停止摄像头失败"
                logger.error(f"停止摄像头失败 {camera_id}: {error_msg}")
                raise ValueError(error_msg)

            # 3. 验证进程已停止（业务规则）
            # 给进程一点时间停止
            import time

            time.sleep(0.5)

            final_status = self.scheduler.get_status(camera_id)
            if final_status.get("running"):
                logger.warning(f"摄像头 {camera_id} 进程可能仍在运行，" "系统将在后台继续尝试停止")

            # 4. 记录成功日志
            logger.info(f"✓ 摄像头停止成功 {camera_id}")

            # TODO: 发布领域事件 CameraStoppedEvent

            return res

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"停止摄像头异常 {camera_id}: {e}")
            raise ValueError(f"停止摄像头失败: {e}")

    def restart_camera(self, camera_id: str) -> Dict[str, Any]:
        """重启指定摄像头的检测进程.

        Args:
            camera_id: 摄像头ID

        Returns:
            包含重启结果的字典

        Raises:
            ValueError: 如果重启失败
        """
        try:
            res = self.scheduler.restart_detection(camera_id)
            if not res.get("ok"):
                logger.error(f"重启摄像头失败 {camera_id}: {res}")
                raise ValueError(res.get("error") or "重启摄像头失败")

            logger.info(
                f"摄像头重启成功 {camera_id}: pid={res.get('pid')} log={res.get('log')}"
            )
            return res

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"重启摄像头异常 {camera_id}: {e}")
            raise ValueError(f"重启摄像头失败: {e}")

    def get_camera_status(self, camera_id: str) -> Dict[str, Any]:
        """获取指定摄像头检测进程的状态.

        Args:
            camera_id: 摄像头ID

        Returns:
            包含状态信息的字典
        """
        try:
            res = self.scheduler.get_status(camera_id)
            logger.debug(
                f"摄像头状态 {camera_id}: running={res.get('running')} pid={res.get('pid')}"
            )
            return res

        except Exception as e:
            logger.error(f"获取摄像头状态异常 {camera_id}: {e}")
            raise ValueError(f"获取摄像头状态失败: {e}")

    def get_batch_status(
        self, camera_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """批量查询摄像头运行状态.

        Args:
            camera_ids: 摄像头ID列表，None表示查询所有

        Returns:
            包含所有摄像头状态的字典
        """
        try:
            result = self.scheduler.get_batch_status(camera_ids)
            logger.debug(f"批量状态查询: {len(result)} 个摄像头")
            return result

        except Exception as e:
            logger.error(f"批量状态查询异常: {e}")
            raise ValueError(f"批量状态查询失败: {e}")

    async def activate_camera(self, camera_id: str) -> Dict[str, Any]:
        """激活摄像头（允许启动检测）.

        Args:
            camera_id: 摄像头ID

        Returns:
            包含激活结果的字典

        Raises:
            ValueError: 如果摄像头不存在
        """
        try:
            # 更新摄像头状态为激活
            updates = {"active": True}
            await self.camera_service.update_camera(camera_id, updates)

            logger.info(f"摄像头激活成功 {camera_id}")
            return {"ok": True, "camera_id": camera_id, "active": True}

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"激活摄像头异常 {camera_id}: {e}")
            raise ValueError(f"激活摄像头失败: {e}")

    async def deactivate_camera(self, camera_id: str) -> Dict[str, Any]:
        """停用摄像头（禁止启动检测，如正在运行则先停止）.

        Args:
            camera_id: 摄像头ID

        Returns:
            包含停用结果的字典

        Raises:
            ValueError: 如果摄像头不存在
        """
        try:
            # 1. 先检查并停止运行中的进程
            status = self.scheduler.status(camera_id)

            was_running = False
            if status.get("running"):
                logger.info(f"摄像头正在运行 {camera_id}，先停止")
                stop_res = self.scheduler.stop_detection(camera_id)
                was_running = stop_res.get("ok", False)
                if not was_running:
                    logger.warning(f"停止摄像头失败 {camera_id}: {stop_res}")

            # 2. 更新配置为停用
            updates = {"active": False, "auto_start": False}
            await self.camera_service.update_camera(camera_id, updates)

            logger.info(f"摄像头停用成功 {camera_id}")
            return {
                "ok": True,
                "camera_id": camera_id,
                "active": False,
                "stopped": was_running,
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"停用摄像头异常 {camera_id}: {e}")
            raise ValueError(f"停用摄像头失败: {e}")

    async def toggle_auto_start(
        self, camera_id: str, auto_start: bool
    ) -> Dict[str, Any]:
        """切换摄像头的自动启动设置.

        Args:
            camera_id: 摄像头ID
            auto_start: 是否自动启动

        Returns:
            包含切换结果的字典

        Raises:
            ValueError: 如果摄像头不存在或未激活
        """
        try:
            # 检查摄像头是否存在和激活状态
            # 注意：这里需要先获取摄像头信息，但为了简化，我们直接更新
            # 如果摄像头不存在或未激活，update_camera会抛出异常

            updates = {"auto_start": bool(auto_start)}
            await self.camera_service.update_camera(camera_id, updates)

            logger.info(f"自动启动设置更新 {camera_id}: {auto_start}")
            return {"ok": True, "camera_id": camera_id, "auto_start": bool(auto_start)}

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"切换自动启动异常 {camera_id}: {e}")
            raise ValueError(f"切换自动启动失败: {e}")

    def get_camera_logs(self, camera_id: str, lines: int = 100) -> Dict[str, Any]:
        """获取指定摄像头的最新日志.

        Args:
            camera_id: 摄像头ID
            lines: 返回的日志行数（默认100）

        Returns:
            包含日志内容的字典

        Raises:
            ValueError: 如果日志文件未配置或读取失败
        """
        try:
            status = self.scheduler.status(camera_id)

            if not status.get("log"):
                raise ValueError("日志文件未配置")

            log_path = FilePath(status["log"])
            if not log_path.exists():
                return {
                    "camera_id": camera_id,
                    "log_file": str(log_path),
                    "lines": [],
                    "message": "日志文件不存在（进程可能尚未启动）",
                }

            with open(log_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                recent_lines = (
                    all_lines[-lines:] if len(all_lines) > lines else all_lines
                )

            return {
                "camera_id": camera_id,
                "log_file": str(log_path),
                "total_lines": len(all_lines),
                "lines": [line.rstrip("\n") for line in recent_lines],
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"读取日志文件异常 {camera_id}: {e}")
            raise ValueError(f"读取日志文件失败: {e}")

    def refresh_all_cameras(self) -> Dict[str, Any]:
        """刷新所有摄像头状态（占位实现）.

        前端仅用来触发状态刷新流程，随后会重新获取摄像头列表.
        这里返回简单的确认信息即可，未来可在此集成真实状态探测/进程同步.

        Returns:
            包含刷新结果的字典
        """
        return {
            "status": "success",
            "message": "所有摄像头状态已刷新",
            "timestamp": datetime.now().isoformat(),
        }
