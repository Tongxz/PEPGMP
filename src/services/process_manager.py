from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

import yaml


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
        return {"cameras": []}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data.get("cameras"), list):
        data["cameras"] = []
    return data


def _pid_file(camera_id: str) -> str:
    return os.path.join(_pids_dir(), f"{camera_id}.pid")


def _log_file(camera_id: str) -> str:
    os.makedirs(_logs_dir(), exist_ok=True)
    return os.path.join(_logs_dir(), f"detect_{camera_id}.log")


def _is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        # 优先使用 psutil（若可用）
        try:
            import psutil  # type: ignore

            return psutil.pid_exists(pid) and (psutil.Process(pid).status() != psutil.STATUS_ZOMBIE)  # type: ignore
        except Exception:
            # 通用探测
            os.kill(pid, 0)
            return True
    except Exception:
        return False


class ProcessManager:
    def __init__(self) -> None:
        self.project_root = _project_root()
        self.cameras_path = _cameras_yaml_path()

    def list_cameras(self) -> List[Dict[str, Any]]:
        data = _read_yaml(self.cameras_path)
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
        str(cam.get("frame_skip", "auto"))
        bool(cam.get("auto_tune", True))

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
        # 可选参数
        if device and device != "auto":
            cmd += ["--device", device]
        if imgsz and imgsz != "auto":
            cmd += ["--imgsz", str(imgsz)]
        # 日志限流默认 120 帧
        cmd += ["--log-interval", "120"]
        # 区域 OSD 可由需要开启
        # cmd += ["--osd-regions"]

        # Windows 设备/自动调优：保留由 main.py 内部自动判定（后续接入 hardware_probe）
        env = os.environ.copy()
        # camera 自定义 env 覆盖
        cam_env: Dict[str, Any] = cam.get("env", {}) or {}
        for k, v in cam_env.items():
            env[str(k)] = str(v)

        return cmd

    def start(self, camera_id: str) -> Dict[str, Any]:
        cams = self.list_cameras()
        cam = next((c for c in cams if str(c.get("id")) == str(camera_id)), None)
        if not cam:
            return {"ok": False, "error": "Camera not found"}
        
        # 检查摄像头是否激活（支持新旧字段）
        is_active = cam.get("active", cam.get("enabled", True))
        if not is_active:
            return {
                "ok": False,
                "error": "摄像头未激活，请先激活后再启动"
            }
        
        pid_path = _pid_file(camera_id)
        # 若已在运行则返回状态
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
        # Windows: 创建新进程组，便于停止
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

        proc = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            stdout=stdout,
            stderr=stderr,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=(os.name != "nt"),
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
        try:
            if pid > 0 and _is_process_alive(pid):
                if os.name == "nt":
                    # Windows: 发送 CTRL_BREAK_EVENT 到进程组
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except Exception:
                        pass
                else:
                    os.kill(pid, signal.SIGTERM)
                # 等待退出
                t0 = time.time()
                while time.time() - t0 < 5.0 and _is_process_alive(pid):
                    time.sleep(0.2)
                if _is_process_alive(pid):
                    if os.name == "nt":
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except Exception:
                            pass
                    else:
                        os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
        try:
            os.remove(pid_path)
        except Exception:
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


# 单例
_manager: Optional[ProcessManager] = None


def get_process_manager() -> ProcessManager:
    global _manager
    if _manager is None:
        _manager = ProcessManager()
    return _manager
