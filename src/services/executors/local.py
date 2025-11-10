"""
Local Process Executor: Manages detection processes on the local machine.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from typing import Any, Dict, List

import yaml

from src.services.executors.base import AbstractProcessExecutor


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
    os.makedirs(_logs_dir(), exist_ok=True)
    return os.path.join(_logs_dir(), f"detect_{camera_id}.log")


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

    def list_cameras(self) -> List[Dict[str, Any]] | Dict[str, Any]:
        data = _read_yaml(self.cameras_path)
        if "error" in data:
            return data  # Propagate the error dictionary
        return list(data.get("cameras", []))

    def _build_command(self, cam: Dict[str, Any]) -> List[str]:
        python_exe = sys.executable
        main_py = os.path.join(self.project_root, "main.py")
        camera_id = str(cam.get("id"))
        source = str(cam.get("source"))
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
        cmd += ["--log-interval", "120"]

        env = os.environ.copy()

        # 确保Redis环境变量被传递（如果未设置，使用默认值）
        if "REDIS_URL" not in env:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = os.getenv("REDIS_PORT", "6379")
            redis_db = os.getenv("REDIS_DB", "0")
            redis_password = os.getenv(
                "REDIS_PASSWORD", "pyt_dev_redis"
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

    def start(self, camera_id: str) -> Dict[str, Any]:
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

        is_active = cam.get("active", cam.get("enabled", True))
        if not is_active:
            return {"ok": False, "error": "摄像头未激活，请先激活后再启动"}

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

        cmd = self._build_command(cam)
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

    def restart(self, camera_id: str) -> Dict[str, Any]:
        self.stop(camera_id)
        time.sleep(0.5)
        return self.start(camera_id)

    def status(self, camera_id: str) -> Dict[str, Any]:
        pid_path = _pid_file(camera_id)
        log_path = _log_file(camera_id)
        pid = 0
        running = False
        if os.path.exists(pid_path):
            try:
                with open(pid_path, "r", encoding="utf-8") as f:
                    pid = int(f.read().strip() or "0")
                running = _is_process_alive(pid)
            except Exception:
                running = False
        return {"ok": True, "running": running, "pid": pid, "log": log_path}

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
