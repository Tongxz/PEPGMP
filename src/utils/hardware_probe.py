from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional


def _safe_import_torch():
    try:
        import torch  # type: ignore

        return torch
    except Exception:
        return None


def _gpu_info_pynvml() -> Dict[str, Any]:
    info: Dict[str, Any] = {"gpu_name": None, "vram_gb": None, "device_count": 0}
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        info["device_count"] = int(count)
        if count > 0:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            info["gpu_name"] = name.decode("utf-8") if hasattr(name, "decode") else str(name)
            info["vram_gb"] = round(float(mem.total) / (1024 ** 3), 1)
    except Exception as e:
        # 如果pynvml失败，尝试使用torch获取信息
        print(f"pynvml failed: {e}, trying torch fallback")
        pass
    return info


def detect_environment() -> Dict[str, Any]:
    """探测当前硬件/运行环境（跨平台，Windows 优先 CUDA）。"""
    env: Dict[str, Any] = {
        "platform": sys.platform,
        "cpu_cores": os.cpu_count() or 1,
        "has_cuda": False,
        "gpu_name": None,
        "vram_gb": None,
        "device_count": 0,
    }
    torch = _safe_import_torch()
    if torch is not None:
        try:
            env["has_cuda"] = bool(torch.cuda.is_available())
            if env["has_cuda"]:
                env["device_count"] = int(torch.cuda.device_count())
                try:
                    env["gpu_name"] = str(torch.cuda.get_device_name(0))
                    # 使用torch获取显存信息作为pynvml的fallback
                    if torch.cuda.is_available():
                        mem_info = torch.cuda.mem_get_info(0)  # (free, total)
                        env["vram_gb"] = round(float(mem_info[1]) / (1024 ** 3), 1)
                except Exception as e:
                    print(f"torch GPU info failed: {e}")
                    pass
        except Exception:
            env["has_cuda"] = False

    # 优先使用 pynvml 获取更准确信息（会覆盖torch的结果）
    nv = _gpu_info_pynvml()
    for k, v in nv.items():
        if v is not None:
            env[k] = v

    return env


def decide_policy(
    preferred_profile: Optional[str] = None,
    user_device: Optional[str] = None,
    user_imgsz: Optional[int] = None,
) -> Dict[str, Any]:
    """根据探测结果给出运行策略（device/imgsz/weights/thread/env）。

    返回示例：
      {
        "device": "cuda"|"cpu",
        "imgsz": 640,
        "human_weights": "models/yolo/yolov8s.pt",
        "env": {"OMP_NUM_THREADS": "8", "MKL_NUM_THREADS": "8"}
      }
    """
    env = detect_environment()
    policy: Dict[str, Any] = {"env": {}}

    # 设备选择
    if user_device and user_device.lower() in ("cuda", "cpu", "mps"):
        policy["device"] = user_device.lower()
    else:
        policy["device"] = "cuda" if env.get("has_cuda") else "cpu"

    # 线程/环境变量（保守值）
    cores = int(env.get("cpu_cores", 4) or 4)
    th = str(min(8, max(1, cores)))
    policy["env"]["OMP_NUM_THREADS"] = th
    policy["env"]["MKL_NUM_THREADS"] = th

    # imgsz/权重（按显存初步估计）
    vram = env.get("vram_gb")
    if user_imgsz:
        policy["imgsz"] = int(user_imgsz)
    else:
        if policy["device"] == "cuda" and isinstance(vram, (int, float)):
            if vram >= 16:
                policy["imgsz"] = 640
                policy["human_weights"] = "models/yolo/yolov8m.pt"
            elif vram >= 8:
                policy["imgsz"] = 640
                policy["human_weights"] = "models/yolo/yolov8s.pt"
            else:
                policy["imgsz"] = 512
                policy["human_weights"] = "models/yolo/yolov8n.pt"
        else:
            policy["imgsz"] = 512
            policy["human_weights"] = "models/yolo/yolov8n.pt"

    # profile 保持用户优先，不强制覆盖
    if preferred_profile:
        policy["profile"] = preferred_profile
    return policy


