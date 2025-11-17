"""模型配置管理模块.

包含各种检测模型的配置类和统一的配置管理器.
"""
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class YOLOConfig:
    """YOLO模型配置."""

    model_path: str = "models/yolo/yolov8n.pt"
    input_size: tuple = (640, 640)
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.45
    max_detections: int = 100
    classes: Optional[List[int]] = None  # None表示检测所有类别
    device: str = "auto"

    def __post_init__(self):
        """初始化后处理."""
        if self.classes is None:
            self.classes = [0]  # 默认只检测人体 (COCO class 0)


@dataclass
class PoseEstimationConfig:
    """姿态估计模型配置."""

    model_type: str = "mediapipe"  # 'mediapipe', 'openpose', 'hrnet'
    model_path: Optional[str] = None
    confidence_threshold: float = 0.5
    tracking_confidence: float = 0.5
    detection_confidence: float = 0.5
    max_num_hands: int = 2
    max_num_faces: int = 1
    max_num_poses: int = 1
    static_image_mode: bool = False
    model_complexity: int = 1  # 0, 1, 2 (for MediaPipe)


@dataclass
class HairnetDetectionConfig:
    """发网检测模型配置."""

    model_path: str = "./models/hairnet_detector.pth"
    input_size: tuple = (224, 224)
    confidence_threshold: float = 0.7
    batch_size: int = 8
    device: str = "auto"
    preprocessing: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化后处理."""
        if self.preprocessing is None:
            self.preprocessing = {
                "normalize": True,
                "mean": [0.485, 0.456, 0.406],
                "std": [0.229, 0.224, 0.225],
            }


@dataclass
class HandwashDetectionConfig:
    """洗手检测模型配置."""

    model_path: str = "./models/handwash_detector.pth"
    sequence_length: int = 16  # 时序模型的序列长度
    input_size: tuple = (224, 224)
    confidence_threshold: float = 0.6
    min_duration: float = 15.0  # 最小洗手时间（秒）
    max_duration: float = 60.0  # 最大洗手时间（秒）
    device: str = "auto"


@dataclass
class SanitizeDetectionConfig:
    """消毒检测模型配置."""

    model_path: str = "./models/sanitize_detector.pth"
    input_size: tuple = (224, 224)
    confidence_threshold: float = 0.6
    min_duration: float = 3.0  # 最小消毒时间（秒）
    max_duration: float = 30.0  # 最大消毒时间（秒）
    hand_distance_threshold: int = 100  # 双手距离阈值（像素）
    device: str = "auto"


@dataclass
class SelfLearningConfig:
    """自学习模型配置."""

    enabled: bool = True
    learning_rate: float = 0.001
    batch_size: int = 16
    update_frequency: int = 100  # 每N个样本更新一次模型
    confidence_threshold: float = 0.8  # 用于自动标注的置信度阈值
    max_samples_per_class: int = 1000
    validation_split: float = 0.2
    early_stopping_patience: int = 10
    model_save_frequency: int = 500  # 每N次更新保存一次模型


class ModelConfig:
    """模型配置管理器."""

    def __init__(self):
        """初始化模型配置."""
        self.yolo = YOLOConfig()
        self.pose_estimation = PoseEstimationConfig()
        self.hairnet_detection = HairnetDetectionConfig()
        self.handwash_detection = HandwashDetectionConfig()
        self.sanitize_detection = SanitizeDetectionConfig()
        self.self_learning = SelfLearningConfig()

        # 模型路径映射
        self.model_paths = {
            "yolo": self.yolo.model_path,
            "hairnet": self.hairnet_detection.model_path,
            "handwash": self.handwash_detection.model_path,
            "sanitize": self.sanitize_detection.model_path,
        }

    def get_model_config(self, model_name: str) -> Optional[Any]:
        """获取指定模型的配置.

        Args:
            model_name: 模型名称

        Returns:
            模型配置对象
        """
        config_map = {
            "yolo": self.yolo,
            "pose_estimation": self.pose_estimation,
            "hairnet_detection": self.hairnet_detection,
            "handwash_detection": self.handwash_detection,
            "sanitize_detection": self.sanitize_detection,
            "self_learning": self.self_learning,
        }

        return config_map.get(model_name)

    def update_model_config(self, model_name: str, **kwargs) -> bool:
        """更新模型配置.

        Args:
            model_name: 模型名称
            **kwargs: 配置参数

        Returns:
            True if successfully updated
        """
        config = self.get_model_config(model_name)
        if config is None:
            return False

        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        return True

    def validate_model_paths(self) -> Dict[str, bool]:
        """验证模型文件是否存在.

        Returns:
            模型文件存在状态字典
        """
        status = {}

        for model_name, model_path in self.model_paths.items():
            if model_path.endswith(".pt") or model_path.endswith(".pth"):
                # 对于PyTorch模型文件，检查文件是否存在
                status[model_name] = os.path.exists(model_path)
            else:
                # 对于其他类型（如MediaPipe），标记为可用
                status[model_name] = True

        return status

    def select_device(self, requested: Optional[str] = None) -> str:
        """统一选择设备，支持环境变量与优先级回退。

        优先级：传入 requested > 环境变量 HBD_DEVICE > auto（mps→cuda→cpu）。

        Args:
            requested: 显式请求的设备（'cpu'|'cuda'|'mps'|'auto'|None）

        Returns:
            最终设备字符串：'cpu'|'cuda'|'mps'
        """
        try:
            import torch
            logger.debug(f"[设备选择] 开始选择设备，请求: {requested}")
            logger.debug(f"[设备选择] PyTorch版本: {torch.__version__}")
            logger.debug(f"[设备选择] torch.cuda.is_available() = {torch.cuda.is_available()}")
        except Exception:
            logger.warning("PyTorch 未安装，强制使用 CPU 设备")
            return "cpu"

        env_req = (os.getenv("HBD_DEVICE", "") or "").strip().lower()
        device_req = (
            (requested or env_req or self.yolo.device or "auto").strip().lower()
        )

        def _mps_available() -> bool:
            return bool(getattr(torch.backends, "mps", None)) and bool(
                torch.backends.mps.is_available()
            )

        def _cuda_available() -> bool:
            try:
                # 直接使用外层作用域的 torch（已在 select_device 函数开始时导入）
                # 使用闭包变量，直接引用外层函数的 torch
                # 注意：这里不能使用 locals() 或 globals()，因为内层函数的作用域不同
                # 应该直接使用外层作用域的 torch 变量
                
                # 尝试从外层作用域获取 torch
                # 由于 Python 的作用域规则，内层函数可以直接访问外层函数的局部变量
                # 但这里 torch 是在 select_device 函数中导入的，所以可以直接使用
                try:
                    # 直接使用外层作用域的 torch（闭包变量）
                    torch_obj = torch  # 这里直接使用外层函数的 torch 变量
                except NameError:
                    # 如果外层作用域没有 torch，则重新导入
                    import torch
                    torch_obj = torch
                
                available = bool(torch_obj.cuda.is_available())
                # 输出诊断信息（使用 INFO 级别，确保可见）
                logger.info(f"[CUDA检查] PyTorch版本: {torch_obj.__version__}, CUDA可用: {available}")
                if hasattr(torch_obj, '__file__'):
                    logger.info(f"[CUDA检查] torch模块路径: {torch_obj.__file__}")
                if hasattr(torch_obj.version, 'cuda') and torch_obj.version.cuda:
                    logger.info(f"[CUDA检查] CUDA编译版本: {torch_obj.version.cuda}")
                else:
                    logger.warning(f"[CUDA检查] PyTorch是CPU版本，不支持CUDA")
                
                if not available:
                    # 输出详细的诊断信息（使用 INFO 级别，确保可见）
                    logger.info(f"[CUDA诊断] PyTorch版本: {torch_obj.__version__}")
                    logger.info(f"[CUDA诊断] torch.cuda.is_available() = {available}")
                    
                    # 检查 PyTorch 是否支持 CUDA
                    has_cuda_attr = hasattr(torch_obj.version, 'cuda')
                    cuda_version = getattr(torch_obj.version, 'cuda', None) if has_cuda_attr else None
                    has_cuda_support = has_cuda_attr and cuda_version is not None
                    
                    if has_cuda_support:
                        logger.warning(f"[CUDA诊断] PyTorch支持CUDA (编译版本: {cuda_version})，但运行时检测不到GPU")
                        logger.warning(f"[CUDA诊断] 可能原因:")
                        logger.warning(f"  1. GPU驱动未安装或版本不匹配")
                        logger.warning(f"  2. CUDA运行时库未正确安装")
                        logger.warning(f"  3. GPU被其他进程占用")
                        logger.warning(f"  4. 环境变量配置问题")
                    else:
                        logger.warning(f"[CUDA诊断] PyTorch是CPU版本，不支持CUDA")
                        logger.warning(f"[CUDA诊断] 解决方案: 安装CUDA版本的PyTorch")
                        logger.warning(f"[CUDA诊断] 例如: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121")
                    
                    # 检查环境变量
                    cuda_path = os.environ.get('CUDA_PATH') or os.environ.get('CUDA_HOME')
                    if cuda_path:
                        logger.info(f"[CUDA诊断] 环境变量 CUDA_PATH/CUDA_HOME: {cuda_path}")
                    else:
                        logger.warning(f"[CUDA诊断] 未设置 CUDA_PATH 或 CUDA_HOME 环境变量")
                    
                    # 尝试运行 nvidia-smi（如果可用）
                    try:
                        import subprocess
                        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            logger.info(f"[CUDA诊断] nvidia-smi 可用，GPU驱动正常")
                            # 提取驱动版本
                            for line in result.stdout.split('\n'):
                                if 'Driver Version' in line:
                                    logger.info(f"[CUDA诊断] {line.strip()}")
                        else:
                            logger.warning(f"[CUDA诊断] nvidia-smi 不可用或返回错误")
                    except Exception as nv_error:
                        logger.warning(f"[CUDA诊断] 无法运行 nvidia-smi: {nv_error}")
                
                return available
            except Exception as e:
                logger.error(f"[CUDA诊断] 检查CUDA可用性时出错: {e}", exc_info=True)
                return False

        # 标准化请求
        if device_req not in {"cpu", "cuda", "mps", "auto"}:
            logger.warning(f"未知的设备请求 '{device_req}'，回退为 'auto'")
            device_req = "auto"

        # 处理显式请求
        if device_req in {"cpu", "cuda", "mps"}:
            if device_req == "mps":
                if _mps_available():
                    logger.info("Device selected: mps (explicit)")
                    return "mps"
                else:
                    logger.warning("MPS 请求但不可用：可能 PyTorch 未启用 MPS 或硬件不支持，回退策略将生效")
                    # 回退到 auto 选择
                    device_req = "auto"
            if device_req == "cuda":
                if _cuda_available():
                    logger.info("Device selected: cuda (explicit)")
                    return "cuda"
                else:
                    logger.warning("CUDA 请求但不可用：未检测到 CUDA GPU 或 CUDA 未正确安装，回退策略将生效")
                    device_req = "auto"
            if device_req == "cpu":
                logger.info("Device selected: cpu (explicit)")
                return "cpu"

        # auto 策略：mps → cuda → cpu
        if _mps_available():
            logger.info("Device selected: mps (auto)")
            return "mps"
        
        # 检查 CUDA 可用性（带详细诊断）
        cuda_available = _cuda_available()
        if cuda_available:
            logger.info("Device selected: cuda (auto)")
            return "cuda"
        else:
            # CUDA 不可用时，输出详细诊断信息
            # 注意：这里不应该输出警告，因为 _cuda_available() 已经输出了详细的诊断信息
            # 只有在确实检测不到 CUDA 时才输出这个警告
            logger.warning("MPS/CUDA 不可用，使用 CPU")
            logger.warning("请检查 [CUDA检查] 和 [CUDA诊断] 日志以获取详细信息")
            # 诊断信息已在 _cuda_available() 中输出
            return "cpu"

    def get_device_config(self) -> str:
        """保留旧接口：获取设备配置（内部走统一选择逻辑）。"""
        return self.select_device(requested=self.yolo.device)

    def get_memory_requirements(self) -> Dict[str, str]:
        """获取模型内存需求估算.

        Returns:
            内存需求字典
        """
        requirements = {
            "yolo": "200-500MB",
            "pose_estimation": "50-100MB",
            "hairnet_detection": "100-200MB",
            "handwash_detection": "150-300MB",
            "sanitize_detection": "100-200MB",
            "total_estimated": "600MB-1.3GB",
        }

        return requirements

    def optimize_for_device(self, device_type: str):
        """根据设备类型优化配置.

        Args:
            device_type: 设备类型 ('cpu', 'cuda', 'edge')
        """
        if device_type == "cpu":
            # CPU优化：减少批量大小，降低模型复杂度
            self.yolo.input_size = (416, 416)
            self.hairnet_detection.batch_size = 4
            self.handwash_detection.sequence_length = 8
            self.pose_estimation.model_complexity = 0

        elif device_type == "cuda":
            # GPU优化：可以使用更大的批量和更高的分辨率
            self.yolo.input_size = (640, 640)
            self.hairnet_detection.batch_size = 16
            self.handwash_detection.sequence_length = 16
            self.pose_estimation.model_complexity = 2

        elif device_type == "edge":
            # 边缘设备优化：最小化资源使用
            self.yolo.model_path = "models/yolo/yolov8n.pt"  # 使用nano版本
            self.yolo.input_size = (320, 320)
            self.hairnet_detection.batch_size = 2
            self.handwash_detection.sequence_length = 4
            self.pose_estimation.model_complexity = 0
            self.pose_estimation.max_num_hands = 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式.

        Returns:
            配置字典.
        """
        from dataclasses import asdict

        return {
            "yolo": asdict(self.yolo),
            "pose_estimation": asdict(self.pose_estimation),
            "hairnet_detection": asdict(self.hairnet_detection),
            "handwash_detection": asdict(self.handwash_detection),
            "sanitize_detection": asdict(self.sanitize_detection),
            "self_learning": asdict(self.self_learning),
        }
