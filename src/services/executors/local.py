"""
Local Process Executor: Manages detection processes on the local machine.
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

import yaml

from src.services.executors.base import AbstractProcessExecutor

logger = logging.getLogger(__name__)


# Helper functions kept internal to this module
def _project_root() -> str:
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )


def _cameras_yaml_path() -> str:
    return os.path.join(_project_root(), "config", "cameras.yaml")


def _logs_dir() -> str:
    return os.path.join(_project_root(), "logs")


def _pids_dir() -> str:
    d = os.path.join(_logs_dir(), "pids")
    os.makedirs(d, exist_ok=True)
    return d


def _read_yaml(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"error": f"File does not exist at path: {path}"}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if not isinstance(data.get("cameras"), list):
            data["cameras"] = []

        return data

    except Exception as e:
        return {"error": f"Failed to read or parse YAML file at {path}. Exception: {e}"}


def _pid_file(camera_id: str) -> str:
    return os.path.join(_pids_dir(), f"{camera_id}.pid")


def _log_file(camera_id: str) -> str:
    """获取检测日志文件路径（按分类组织）"""
    logs_base_dir = _logs_dir()
    detection_log_dir = os.path.join(logs_base_dir, "detection")
    os.makedirs(detection_log_dir, exist_ok=True)
    return os.path.join(detection_log_dir, f"detect_{camera_id}.log")


def _is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        try:
            import psutil  # type: ignore

            return psutil.pid_exists(pid) and (psutil.Process(pid).status() != psutil.STATUS_ZOMBIE)  # type: ignore
        except Exception:
            os.kill(pid, 0)
            return True
    except Exception:
        return False


class LocalProcessExecutor(AbstractProcessExecutor):
    """Manages detection processes as local subprocesses."""

    def __init__(self) -> None:
        self.project_root = _project_root()
        self.cameras_path = _cameras_yaml_path()
        self._last_env: Dict[str, str] = {}
        self._camera_repository: Optional[Any] = None

    def _init_camera_repository(self) -> bool:
        """初始化相机仓储（从数据库读取）"""
        if self._camera_repository is not None:
            return True

        try:
            import asyncpg

            from src.infrastructure.repositories.postgresql_camera_repository import (
                PostgreSQLCameraRepository,
            )

            # 获取数据库连接URL
            database_url = os.getenv(
                "DATABASE_URL",
                "postgresql://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development",
            )

            # 在同步上下文中运行异步代码
            async def _create_repository():
                try:
                    pool = await asyncpg.create_pool(
                        database_url,
                        min_size=1,
                        max_size=5,
                        command_timeout=10,  # 10秒超时
                    )
                    repo = PostgreSQLCameraRepository(pool)
                    # 确保表存在
                    await repo._ensure_table_exists()
                    return repo
                except Exception as e:
                    logger.warning(f"创建数据库连接池失败: {e}")
                    return None

            # 尝试创建仓储（在同步上下文中）
            try:
                # 检查是否有正在运行的事件循环
                try:
                    asyncio.get_running_loop()
                    # 如果有事件循环，无法使用asyncio.run，直接返回False
                    logger.debug("检测到已有事件循环，无法初始化数据库仓储，将使用YAML回退")
                    return False
                except RuntimeError:
                    # 没有事件循环，可以使用asyncio.run
                    pass

                # 没有事件循环，直接使用 asyncio.run
                self._camera_repository = asyncio.run(_create_repository())

                if self._camera_repository is not None:
                    logger.info("相机仓储已从数据库初始化")
                    return True
            except Exception as e:
                logger.warning(f"初始化相机仓储失败: {e}，将使用YAML回退")
                return False

        except ImportError as e:
            logger.warning(f"导入数据库依赖失败: {e}，将使用YAML回退")
            return False
        except Exception as e:
            logger.warning(f"初始化相机仓储失败: {e}，将使用YAML回退")
            return False

        return False

    def list_cameras(self) -> List[Dict[str, Any]] | Dict[str, Any]:
        """列出所有相机配置（优先从数据库读取，失败时回退到YAML）

        注意：
        - 在FastAPI环境中，应该通过API层传递相机配置给executor，而不是调用此方法
        - 此方法主要用于命令行启动检测进程时的回退机制
        - YAML文件仅作为最后的回退选项，不应作为主要配置源
        """
        # 尝试从数据库读取（仅在同步上下文中）
        if self._init_camera_repository() and self._camera_repository is not None:
            try:

                async def _fetch_cameras():
                    cameras = await self._camera_repository.find_all()
                    # 转换为字典格式（兼容旧API）
                    cameras_dict = []
                    for camera in cameras:
                        cam_dict = camera.to_dict()
                        # 提取metadata中的字段到顶层（兼容API格式）
                        metadata = cam_dict.get("metadata", {})
                        if "source" in metadata:
                            cam_dict["source"] = metadata["source"]
                        if "log_interval" in metadata:
                            cam_dict["log_interval"] = metadata["log_interval"]
                        if "stream_interval" in metadata:
                            cam_dict["stream_interval"] = metadata["stream_interval"]
                        if "frame_by_frame" in metadata:
                            cam_dict["frame_by_frame"] = metadata["frame_by_frame"]
                        # 提取其他配置字段
                        for key in [
                            "regions_file",
                            "profile",
                            "device",
                            "imgsz",
                            "auto_start",
                        ]:
                            if key in metadata:
                                cam_dict[key] = metadata[key]
                        # 兼容旧格式：active字段
                        cam_dict["active"] = camera.is_active
                        cameras_dict.append(cam_dict)
                    return cameras_dict

                # 在同步上下文中运行异步代码
                try:
                    # 检查是否有正在运行的事件循环
                    try:
                        asyncio.get_running_loop()
                        # 如果有事件循环，无法使用asyncio.run，直接回退到YAML
                        logger.warning(
                            "检测到已有事件循环，无法从数据库读取。" "建议：在API层获取相机配置并传递给executor.start()"
                        )
                        raise RuntimeError("Event loop already running")
                    except RuntimeError as e:
                        # 检查是否是"Event loop already running"异常
                        if "already running" in str(e):
                            raise
                        # 没有事件循环，可以使用asyncio.run

                    # 没有事件循环，直接使用 asyncio.run
                    cameras = asyncio.run(_fetch_cameras())

                    logger.info(f"从数据库读取到 {len(cameras)} 个相机配置")
                    return cameras
                except Exception as e:
                    logger.error(f"从数据库读取相机配置失败: {e}", exc_info=True)
                    raise RuntimeError(
                        f"无法从数据库读取相机配置: {e}。" "请确保数据库服务正在运行，并且DATABASE_URL环境变量已正确设置。"
                    )

            except Exception as e:
                logger.error(f"从数据库读取相机配置时出错: {e}", exc_info=True)
                raise RuntimeError(
                    f"无法从数据库读取相机配置: {e}。" "请确保数据库服务正在运行，并且DATABASE_URL环境变量已正确设置。"
                )

        # 如果到达这里，说明数据库连接未初始化
        raise RuntimeError(
            "无法从数据库读取相机配置：数据库连接未初始化。" "请确保数据库服务正在运行，并且DATABASE_URL环境变量已正确设置。"
        )

    def _build_command(self, cam: Dict[str, Any]) -> List[str]:
        python_exe = sys.executable
        main_py = os.path.join(self.project_root, "main.py")
        camera_id = str(cam.get("id"))

        # 获取source字段，如果不存在则抛出异常
        source = cam.get("source")
        if not source or source == "None" or source is None:
            raise ValueError(
                f"相机配置缺少必填字段 'source': camera_id={camera_id}, "
                f"请检查数据库中的相机配置是否包含 source 字段"
            )
        source = str(source)

        regions_file = str(cam.get("regions_file", "config/regions.json"))
        profile = str(cam.get("profile", "accurate"))
        device = str(cam.get("device", "auto"))
        imgsz = str(cam.get("imgsz", "auto"))

        cmd: List[str] = [
            python_exe,
            main_py,
            "--mode",
            "detection",
            "--source",
            source,
            "--regions-file",
            regions_file,
            "--profile",
            profile,
            "--camera-id",
            camera_id,
        ]
        if device and device != "auto":
            cmd += ["--device", device]
        if imgsz and imgsz != "auto":
            cmd += ["--imgsz", str(imgsz)]
        # 从相机配置中读取log_interval，如果没有则使用默认值120
        log_interval = cam.get("log_interval", 120)
        cmd += ["--log-interval", str(log_interval)]

        env = os.environ.copy()

        # 确保Redis环境变量被传递（如果未设置，使用默认值）
        if "REDIS_URL" not in env:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = os.getenv("REDIS_PORT", "6379")
            redis_db = os.getenv("REDIS_DB", "0")
            redis_password = os.getenv(
                "REDIS_PASSWORD", "pepgmp_dev_redis"
            )  # Docker Redis默认密码
            if redis_password:
                env[
                    "REDIS_URL"
                ] = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                env["REDIS_URL"] = f"redis://{redis_host}:{redis_port}/{redis_db}"

        # 确保视频流相关环境变量被传递
        if "VIDEO_STREAM_USE_REDIS" not in env:
            env["VIDEO_STREAM_USE_REDIS"] = "1"

        cam_env: Dict[str, Any] = cam.get("env", {}) or {}
        for k, v in cam_env.items():
            env[str(k)] = str(v)
        self._last_env = env

        return cmd

    def start(
        self, camera_id: str, camera_config: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        # 如果提供了相机配置，直接使用；否则从列表查找
        if camera_config is not None:
            cam = camera_config
        else:
            cams_or_error = self.list_cameras()
            if isinstance(cams_or_error, dict) and "error" in cams_or_error:
                # Propagate the detailed error from the file reading operation
                return {
                    "ok": False,
                    "error": f"Configuration file error: {cams_or_error['error']}",
                }

            cams = cams_or_error  # Now we know it's a list
            cam = next((c for c in cams if str(c.get("id")) == str(camera_id)), None)
            if not cam:
                return {
                    "ok": False,
                    "error": f"Camera with id '{camera_id}' not found in the configuration.",
                }

        # 检查激活状态
        # 优先使用 active 字段，其次使用 enabled 字段，最后默认为 True
        is_active = cam.get("active", cam.get("enabled", True))

        # 如果 active 字段明确为 False，检查是否从数据库读取（status 字段）
        if not is_active and "status" in cam:
            # 如果 status 是 "active"，则覆盖 active 字段
            if cam.get("status") == "active":
                is_active = True
                cam["active"] = True

        if not is_active:
            camera_id = cam.get("id", camera_id)
            return {
                "ok": False,
                "error": f"摄像头 {camera_id} 未激活，请先激活后再启动。可通过 API /cameras/{camera_id}/activate 激活",
            }

        # 验证必填字段source
        source = cam.get("source")
        if not source or source == "None" or source is None:
            camera_id = cam.get("id", camera_id)
            logger.error(
                f"摄像头 {camera_id} 配置缺少必填字段 'source': "
                f"cam={cam}, metadata={cam.get('metadata', {})}"
            )
            return {
                "ok": False,
                "error": f"摄像头 {camera_id} 配置缺少必填字段 'source'，请检查数据库中的相机配置是否包含 source 字段",
            }

        pid_path = _pid_file(camera_id)
        if os.path.exists(pid_path):
            try:
                with open(pid_path, "r", encoding="utf-8") as f:
                    pid = int(f.read().strip() or "0")
                if _is_process_alive(pid):
                    return {
                        "ok": True,
                        "running": True,
                        "pid": pid,
                        "log": _log_file(camera_id),
                    }
            except Exception:
                pass

        try:
            cmd = self._build_command(cam)
        except ValueError as e:
            logger.error(f"构建启动命令失败: {e}")
            return {
                "ok": False,
                "error": str(e),
            }
        log_path = _log_file(camera_id)
        stdout = open(log_path, "a", encoding="utf-8")
        stderr = stdout

        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            stdout=stdout,
            stderr=stderr,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=(os.name != "nt"),
            env=self._last_env,
        )
        with open(pid_path, "w", encoding="utf-8") as pf:
            pf.write(str(proc.pid))
        return {
            "ok": True,
            "running": True,
            "pid": proc.pid,
            "log": log_path,
            "cmd": cmd,
        }

    def stop(self, camera_id: str) -> Dict[str, Any]:
        pid_path = _pid_file(camera_id)
        if not os.path.exists(pid_path):
            return {"ok": True, "running": False}
        try:
            with open(pid_path, "r", encoding="utf-8") as f:
                pid = int(f.read().strip() or "0")
        except Exception:
            pid = 0

        if pid > 0 and _is_process_alive(pid):
            try:
                if os.name == "nt":
                    os.kill(pid, signal.SIGTERM)
                else:
                    os.kill(pid, signal.SIGTERM)

                t0 = time.time()
                while time.time() - t0 < 5.0 and _is_process_alive(pid):
                    time.sleep(0.2)

                if _is_process_alive(pid):
                    os.kill(pid, signal.SIGKILL)
            except Exception:
                pass  # Process might have died already

        try:
            os.remove(pid_path)
        except OSError:
            pass
        return {"ok": True, "running": False}

    def restart(
        self, camera_id: str, camera_config: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        self.stop(camera_id)
        time.sleep(0.5)
        return self.start(camera_id, camera_config)

    def status(self, camera_id: str) -> Dict[str, Any]:
        pid_path = _pid_file(camera_id)
        log_path = _log_file(camera_id)
        pid = 0
        running = False
        if os.path.exists(pid_path):
            try:
                with open(pid_path, "r", encoding="utf-8") as f:
                    pid_str = f.read().strip()
                    if pid_str:
                        pid = int(pid_str)
                        running = _is_process_alive(pid)
            except (ValueError, OSError) as e:
                logger.warning(
                    f"读取PID文件失败: camera_id={camera_id}, pid_path={pid_path}, error={e}"
                )
                running = False
        else:
            logger.debug(f"PID文件不存在: camera_id={camera_id}, pid_path={pid_path}")

        result = {"ok": True, "running": running, "pid": pid, "log": log_path}
        logger.info(
            f"获取摄像头状态: camera_id={camera_id}, running={running}, pid={pid}, log={log_path}"
        )
        return result

    def start_all(self) -> Dict[str, Any]:
        cams = self.list_cameras()
        started: List[str] = []
        for c in cams:
            cid = str(c.get("id"))
            res = self.start(cid)
            if res.get("ok"):
                started.append(cid)
        return {"ok": True, "started": started}

    def stop_all(self) -> Dict[str, Any]:
        cams = self.list_cameras()
        stopped: List[str] = []
        for c in cams:
            cid = str(c.get("id"))
            res = self.stop(cid)
            if res.get("ok"):
                stopped.append(cid)
        return {"ok": True, "stopped": stopped}
