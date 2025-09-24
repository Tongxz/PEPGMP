"""
GPU加速优化模块
GPU Acceleration Optimization Module

提供跨平台GPU加速优化，自动检测和配置最佳性能设置
"""

import logging
import os
import sys
from typing import Any, Dict

logger = logging.getLogger(__name__)


class GPUAccelerationManager:
    """GPU加速管理器"""

    def __init__(self):
        self.device = "cpu"
        self.gpu_info = {}
        self.optimization_applied = False
        self.performance_config = {}

    def initialize_gpu_acceleration(self) -> Dict[str, Any]:
        """初始化GPU加速"""
        logger.info("🚀 初始化GPU加速优化...")

        results = {
            "platform": sys.platform,
            "device": "cpu",
            "gpu_available": False,
            "optimizations_applied": [],
            "warnings": [],
            "performance_config": {},
        }

        try:
            pass

            # 1. 检测可用设备
            device_info = self._detect_best_device()
            results.update(device_info)

            # 2. 应用平台特定优化
            if device_info["device"] != "cpu":
                platform_opts = self._apply_platform_optimizations(device_info)
                results["optimizations_applied"].extend(platform_opts)

            # 3. 配置PyTorch优化
            torch_opts = self._configure_torch_optimizations(device_info)
            results["optimizations_applied"].extend(torch_opts)

            # 4. 生成性能配置
            perf_config = self._generate_performance_config(device_info)
            results["performance_config"] = perf_config

            self.device = device_info["device"]
            self.gpu_info = device_info
            self.optimization_applied = True
            self.performance_config = perf_config

            logger.info(f"✅ GPU加速初始化完成 - 设备: {self.device}")

        except ImportError:
            results["warnings"].append("PyTorch未安装，使用CPU模式")
            logger.warning("PyTorch未安装，无法启用GPU加速")
        except Exception as e:
            results["warnings"].append(f"GPU加速初始化失败: {e}")
            logger.error(f"GPU加速初始化失败: {e}")

        return results

    def _detect_best_device(self) -> Dict[str, Any]:
        """检测最佳计算设备"""
        import torch

        device_info = {
            "device": "cpu",
            "gpu_available": False,
            "gpu_count": 0,
            "gpu_memory_gb": 0,
            "gpu_name": None,
            "compute_capability": None,
            "backend": "cpu",
        }

        # 1. CUDA检测 (NVIDIA GPU)
        if torch.cuda.is_available():
            device_info.update(
                {
                    "device": "cuda",
                    "gpu_available": True,
                    "gpu_count": torch.cuda.device_count(),
                    "gpu_name": torch.cuda.get_device_name(0),
                    "gpu_memory_gb": torch.cuda.get_device_properties(0).total_memory
                    / (1024**3),
                    "compute_capability": torch.cuda.get_device_capability(0),
                    "backend": "cuda",
                }
            )
            logger.info(
                f"✅ CUDA GPU可用: {device_info['gpu_name']} ({device_info['gpu_memory_gb']:.1f}GB)"
            )

        # 2. MPS检测 (Apple Silicon)
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device_info.update(
                {"device": "mps", "gpu_available": True, "backend": "mps"}
            )
            logger.info("✅ Apple MPS可用")

        # 3. CPU回退
        else:
            logger.info("使用CPU计算")

        return device_info

    def _apply_platform_optimizations(self, device_info: Dict[str, Any]) -> list:
        """应用平台特定优化"""
        optimizations = []

        if device_info["backend"] == "cuda":
            # CUDA优化
            cuda_opts = self._apply_cuda_optimizations(device_info)
            optimizations.extend(cuda_opts)

        elif device_info["backend"] == "mps":
            # MPS优化
            mps_opts = self._apply_mps_optimizations()
            optimizations.extend(mps_opts)

        return optimizations

    def _apply_cuda_optimizations(self, device_info: Dict[str, Any]) -> list:
        """应用CUDA优化设置"""
        optimizations = []

        try:
            import torch

            # 1. 环境变量优化
            cuda_env = {
                "CUDA_LAUNCH_BLOCKING": "0",  # 异步执行
                "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512,roundup_power2_divisions:16",
                "CUBLAS_WORKSPACE_CONFIG": ":16:8",
                "CUDA_MODULE_LOADING": "LAZY",
                "TORCH_CUDNN_V8_API_ENABLED": "1",
            }

            for key, value in cuda_env.items():
                if key not in os.environ:
                    os.environ[key] = value
                    optimizations.append(f"设置环境变量 {key}={value}")

            # 2. CuDNN优化
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.deterministic = False
            optimizations.append("启用CuDNN基准测试优化")

            # 3. TF32优化 (Ampere架构)
            if hasattr(torch.backends.cuda.matmul, "allow_tf32"):
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                optimizations.append("启用TF32精度优化")

            # 4. 内存管理
            torch.cuda.empty_cache()
            optimizations.append("清理GPU内存缓存")

            # 5. 多GPU优化
            if device_info["gpu_count"] > 1:
                optimizations.append(f"检测到{device_info['gpu_count']}个GPU，可启用多GPU并行")

        except Exception as e:
            logger.warning(f"CUDA优化应用失败: {e}")

        return optimizations

    def _apply_mps_optimizations(self) -> list:
        """应用MPS优化设置"""
        optimizations = []

        try:
            # MPS特定优化
            os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
            optimizations.append("启用MPS fallback机制")

        except Exception as e:
            logger.warning(f"MPS优化应用失败: {e}")

        return optimizations

    def _configure_torch_optimizations(self, device_info: Dict[str, Any]) -> list:
        """配置PyTorch优化"""
        optimizations = []

        try:
            import torch

            # 1. 线程优化
            if device_info["backend"] == "cpu":
                num_threads = min(os.cpu_count() or 4, 8)
                torch.set_num_threads(num_threads)
                os.environ.setdefault("OMP_NUM_THREADS", str(num_threads))
                os.environ.setdefault("MKL_NUM_THREADS", str(num_threads))
                optimizations.append(f"设置CPU线程数: {num_threads}")

            # 2. 编译优化 (PyTorch 2.0+)
            if hasattr(torch, "compile"):
                optimizations.append("PyTorch 2.0编译优化可用")

            # 3. JIT优化
            if hasattr(torch.jit, "set_num_threads"):
                torch.jit.set_num_threads(os.cpu_count() or 4)
                optimizations.append("配置JIT线程数")

        except Exception as e:
            logger.warning(f"PyTorch优化配置失败: {e}")

        return optimizations

    def _generate_performance_config(
        self, device_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成性能配置"""
        config = {
            "device": device_info["device"],
            "mixed_precision": device_info["backend"] in ["cuda", "mps"],
            "compile_model": hasattr(__import__("torch"), "compile"),
            "batch_size": self._calculate_optimal_batch_size(device_info),
            "num_workers": self._calculate_optimal_workers(device_info),
            "pin_memory": device_info["gpu_available"],
            "non_blocking": device_info["gpu_available"],
        }

        # CUDA特定配置
        if device_info["backend"] == "cuda":
            config.update(
                {
                    "cudnn_benchmark": True,
                    "allow_tf32": True,
                    "channels_last": True,  # 使用channels_last内存格式
                    "gradient_checkpointing": device_info["gpu_memory_gb"] < 8,  # 小显存启用
                }
            )

        return config

    def _calculate_optimal_batch_size(self, device_info: Dict[str, Any]) -> int:
        """计算最优批处理大小"""
        if device_info["backend"] == "cuda":
            memory_gb = device_info.get("gpu_memory_gb", 4)
            if memory_gb >= 24:
                return 32
            elif memory_gb >= 16:
                return 24
            elif memory_gb >= 12:
                return 16
            elif memory_gb >= 8:
                return 12
            elif memory_gb >= 6:
                return 8
            else:
                return 4
        elif device_info["backend"] == "mps":
            return 8  # MPS保守设置
        else:
            return min(os.cpu_count() or 4, 8)

    def _calculate_optimal_workers(self, device_info: Dict[str, Any]) -> int:
        """计算最优工作线程数"""
        if device_info["gpu_available"]:
            return min(device_info.get("gpu_count", 1) * 2, 8)
        else:
            return min(os.cpu_count() or 4, 8)

    def get_optimized_model_config(self, model_type: str = "yolo") -> Dict[str, Any]:
        """获取优化的模型配置"""
        if not self.optimization_applied:
            self.initialize_gpu_acceleration()

        base_config = self.performance_config.copy()

        # 模型特定优化
        if model_type.lower() == "yolo":
            base_config.update(
                {
                    "imgsz": 640,
                    "conf": 0.4,
                    "iou": 0.6,
                    "half": self.device in ["cuda", "mps"],  # 半精度推理
                    "dnn": True,  # OpenCV DNN后端
                    "augment": False,  # 推理时不启用数据增强
                    "agnostic_nms": False,  # 类别特定的NMS
                    "retina_masks": True,  # 高质量mask
                }
            )
        elif model_type.lower() == "mediapipe":
            base_config.update(
                {
                    "model_complexity": 1,
                    "min_detection_confidence": 0.5,
                    "min_tracking_confidence": 0.5,
                    "max_num_hands": 2,
                    "static_image_mode": False,
                }
            )

        return base_config

    def optimize_model(self, model, model_type: str = "pytorch"):
        """优化模型"""
        if not self.optimization_applied:
            self.initialize_gpu_acceleration()

        try:
            import torch

            # 1. 移动到最佳设备
            if hasattr(model, "to"):
                model = model.to(self.device)

            # 2. 设置评估模式
            if hasattr(model, "eval"):
                model.eval()

            # 3. 半精度优化
            if self.device in ["cuda", "mps"] and hasattr(model, "half"):
                model = model.half()
                logger.info("启用半精度推理")

            # 4. 编译优化 (PyTorch 2.0+)
            if (
                hasattr(torch, "compile")
                and self.performance_config.get("compile_model", False)
                and model_type == "pytorch"
            ):
                try:
                    model = torch.compile(
                        model, mode="reduce-overhead", fullgraph=False, dynamic=True
                    )
                    logger.info("启用PyTorch 2.0编译优化")
                except Exception as e:
                    logger.warning(f"模型编译失败: {e}")

            return model

        except Exception as e:
            logger.warning(f"模型优化失败: {e}")
            return model

    def create_optimized_dataloader(self, dataset, **kwargs):
        """创建优化的数据加载器"""
        if not self.optimization_applied:
            self.initialize_gpu_acceleration()

        try:
            import torch.utils.data as data

            # 使用性能配置
            dataloader_config = {
                "batch_size": kwargs.get(
                    "batch_size", self.performance_config["batch_size"]
                ),
                "num_workers": kwargs.get(
                    "num_workers", self.performance_config["num_workers"]
                ),
                "pin_memory": kwargs.get(
                    "pin_memory", self.performance_config["pin_memory"]
                ),
                "persistent_workers": kwargs.get("persistent_workers", True),
                "prefetch_factor": kwargs.get("prefetch_factor", 2),
            }

            # 合并用户配置
            dataloader_config.update(kwargs)

            return data.DataLoader(dataset, **dataloader_config)

        except ImportError:
            logger.warning("PyTorch不可用，无法创建优化的数据加载器")
            return None


# 全局单例
_gpu_manager = None


def get_gpu_manager() -> GPUAccelerationManager:
    """获取GPU管理器单例"""
    global _gpu_manager
    if _gpu_manager is None:
        _gpu_manager = GPUAccelerationManager()
    return _gpu_manager


def initialize_gpu_acceleration() -> Dict[str, Any]:
    """初始化GPU加速（便捷函数）"""
    manager = get_gpu_manager()
    return manager.initialize_gpu_acceleration()


def get_optimized_device() -> str:
    """获取优化的设备（便捷函数）"""
    manager = get_gpu_manager()
    if not manager.optimization_applied:
        manager.initialize_gpu_acceleration()
    return manager.device


def optimize_model_for_inference(model, model_type: str = "pytorch"):
    """优化模型用于推理（便捷函数）"""
    manager = get_gpu_manager()
    return manager.optimize_model(model, model_type)


def get_optimal_batch_size() -> int:
    """获取最优批处理大小（便捷函数）"""
    manager = get_gpu_manager()
    if not manager.optimization_applied:
        manager.initialize_gpu_acceleration()
    return manager.performance_config.get("batch_size", 4)


# 自动初始化（在模块导入时）
if __name__ != "__main__":
    try:
        # 在非测试环境下自动初始化
        if "pytest" not in sys.modules:
            initialize_gpu_acceleration()
    except Exception:
        pass  # 静默失败，避免影响导入
