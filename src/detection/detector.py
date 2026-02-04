import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
import torch
from ultralytics import YOLO

# 导入统一参数配置
from src.config.unified_params import get_unified_params

logger = logging.getLogger(__name__)


class BaseDetector(ABC):
    """检测器抽象基类"""

    def __init__(self, model_path: str, device: str = "auto"):
        """
        初始化检测器

        Args:
            model_path: 模型路径
            device: 计算设备
        """
        self.model_path = model_path
        self.device = self._get_device(device)
        self.model = self._load_model(model_path)

    def _get_device(self, device: str) -> str:
        """获取计算设备"""
        if device == "auto":
            try:
                # 优先 MPS (Apple Silicon) → CUDA → CPU
                mps_built = bool(getattr(torch.backends, "mps", None))
                mps_available = mps_built and bool(torch.backends.mps.is_available())
                if mps_available:
                    return "mps"
                if torch.cuda.is_available():
                    return "cuda"
            except Exception:
                pass
            return "cpu"
        return device

    @abstractmethod
    def _load_model(self, model_path: str):
        """加载模型"""

    @abstractmethod
    def detect(self, image: np.ndarray) -> List[Dict]:
        """执行检测"""

    def visualize(self, image: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """可视化检测结果"""
        result_image = image.copy()
        for detection in detections:
            bbox = detection.get("bbox")
            if bbox:
                x1, y1, x2, y2 = [int(coord) for coord in bbox]
                cv2.rectangle(result_image, (x1, y1), (x2, y2), (0, 255, 0), 2)

            label = self._get_label(detection)
            if label:
                cv2.putText(
                    result_image,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 255, 0),
                    2,
                )
        return result_image

    def _get_label(self, detection: Dict) -> str:
        """获取用于可视化的标签"""
        label = detection.get("class_name", "")
        confidence = detection.get("confidence")
        if confidence:
            label += f" {confidence:.2f}"
        return label.strip()


class HumanDetector(BaseDetector):
    """人体检测器

    基于YOLOv8的人体检测模块，支持实时检测和批量处理
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "auto",
        auto_convert_tensorrt: Optional[bool] = None,
    ):
        """
        初始化人体检测器

        Args:
            model_path: YOLO模型路径，如果为None则使用统一配置
            device: 计算设备 ('cpu', 'cuda', 'auto')
            auto_convert_tensorrt: 是否自动转换为TensorRT（如果可用）
                                 如果为None，则从环境变量AUTO_CONVERT_TENSORRT读取
                                 环境变量未设置时默认为True（保持向后兼容）
        """
        # 获取统一参数配置
        self.params = get_unified_params().human_detection

        # 使用统一配置或传入参数
        model_path = model_path if model_path is not None else self.params.model_path

        # 解析 device：如果为 "auto"，需要先解析为实际设备
        if device == "auto":
            device = self.params.device
        # 如果统一配置中的 device 也是 "auto"，需要通过 ModelConfig 解析
        if device == "auto":
            from src.config.model_config import ModelConfig

            config = ModelConfig()
            device = config.select_device(requested=None)
            logger.info(f"设备 'auto' 已解析为: {device}")

        # 确定是否启用TensorRT自动转换
        # 优先级：显式参数 > 环境变量 > 默认值True（向后兼容）
        if auto_convert_tensorrt is None:
            env_value = os.getenv("AUTO_CONVERT_TENSORRT", "").strip().lower()
            if env_value:
                # 环境变量已设置，解析值
                auto_convert_tensorrt = env_value in ("true", "1", "yes")
            else:
                # 环境变量未设置，使用默认值True（向后兼容）
                auto_convert_tensorrt = True
            # 使用 INFO 级别，确保在生产环境可见
            logger.info(
                f"TensorRT自动转换配置: 环境变量={env_value if env_value else '(未设置)'}, "
                f"启用状态={auto_convert_tensorrt}"
            )

        # 自动检测并转换TensorRT引擎
        if auto_convert_tensorrt:
            model_path = self._auto_convert_to_tensorrt(model_path, device)
        else:
            logger.info("TensorRT自动转换已禁用，使用PyTorch模型")

        super().__init__(model_path, device)

        # 使用统一参数配置
        self.confidence_threshold = self.params.confidence_threshold
        self.iou_threshold = self.params.iou_threshold
        self.min_box_area = self.params.min_box_area
        self.max_box_ratio = self.params.max_box_ratio
        self.min_width = self.params.min_width
        self.min_height = self.params.min_height
        self.nms_threshold = self.params.nms_threshold
        self.max_detections = self.params.max_detections

        logger.info(
            f"HumanDetector initialized on {self.device} with unified params: "
            f"conf={self.confidence_threshold}, iou={self.iou_threshold}, "
            f"min_area={self.min_box_area}"
        )

    def _auto_convert_to_tensorrt(self, model_path: str, device: str) -> str:
        """
        自动检测并转换为TensorRT引擎

        Args:
            model_path: 原始模型路径
            device: 计算设备

        Returns:
            优化后的模型路径（TensorRT引擎或原始模型）
        """
        try:
            # 只在CUDA设备上使用TensorRT
            if device != "cuda":
                logger.info(f"设备为 {device}，跳过TensorRT转换")
                return model_path

            # 检查TensorRT是否可用
            try:
                import tensorrt as trt

                logger.info(f"TensorRT可用，版本: {trt.__version__}")
            except ImportError:
                logger.info("TensorRT未安装，使用PyTorch模型")
                return model_path

            # 检查CUDA是否可用
            if not torch.cuda.is_available():
                logger.info("CUDA不可用，使用PyTorch模型")
                return model_path

            # 检查模型文件
            pt_file = Path(model_path)
            if not pt_file.exists():
                logger.warning(f"模型文件不存在: {model_path}")
                return model_path

            # 将转换后的文件保存到可写目录（/app/output/models/yolo/）
            # 因为原始模型目录可能是只读的（Docker volume 挂载）
            output_dir = Path("/app/output/models/yolo")
            output_dir.mkdir(parents=True, exist_ok=True)

            # 生成TensorRT引擎路径（保存在可写目录）
            engine_file = output_dir / pt_file.with_suffix(".engine").name

            # 检查是否需要转换
            needs_conversion = False

            if not engine_file.exists():
                logger.info(f"📋 TensorRT引擎不存在，开始转换: {pt_file.name}")
                needs_conversion = True
            elif pt_file.stat().st_mtime > engine_file.stat().st_mtime:
                logger.info(f"📋 PyTorch模型已更新，重新转换: {pt_file.name}")
                needs_conversion = True
            else:
                logger.info(f"✅ TensorRT引擎已存在: {engine_file.name}")
                return str(engine_file)

            # 转换模型
            if needs_conversion:
                logger.info(f"🔄 开始转换为TensorRT: {pt_file.name}")

                import shutil
                import tempfile

                from ultralytics import YOLO

                # 加载模型
                YOLO(str(pt_file))

                # 使用临时目录进行转换（因为 export 方法可能需要在模型目录写入临时文件）
                # 然后将结果文件移动到目标目录
                with tempfile.TemporaryDirectory() as tmpdir:
                    Path(tmpdir) / pt_file.stem

                    # 导出为TensorRT FP16（会生成 .engine 文件）
                    # export 方法会将文件保存到与输入文件相同的目录
                    # 所以我们先复制模型文件到临时目录
                    tmp_pt_file = Path(tmpdir) / pt_file.name
                    shutil.copy2(pt_file, tmp_pt_file)

                    # 在临时目录中导出
                    model_tmp = YOLO(str(tmp_pt_file))
                    exported_path = model_tmp.export(
                        format="engine",
                        device=0,
                        imgsz=640,
                        half=True,  # FP16精度
                        workspace=4,  # 4GB工作空间
                        simplify=True,
                        opset=12,
                        dynamic=False,
                        verbose=False,
                    )

                    # 将生成的 .engine 文件移动到目标目录
                    # export() 方法返回导出文件的路径，通常与输入文件在同一目录
                    exported_engine = Path(exported_path)
                    if exported_engine.exists() and exported_engine.suffix == ".engine":
                        # 直接使用 export() 返回的路径
                        shutil.move(str(exported_engine), str(engine_file))
                        logger.info(f"✅ TensorRT引擎已保存到: {engine_file}")
                    else:
                        # 如果 export 返回的路径不存在或不是 .engine 文件，尝试在临时目录中查找
                        # export() 可能返回 .onnx 文件路径，我们需要找 .engine 文件
                        tmp_engine = Path(tmpdir) / (tmp_pt_file.stem + ".engine")
                        if tmp_engine.exists():
                            shutil.move(str(tmp_engine), str(engine_file))
                            logger.info(f"✅ TensorRT引擎已保存到: {engine_file}")
                        else:
                            # 最后尝试：在临时目录中查找所有 .engine 文件
                            engine_files = list(Path(tmpdir).glob("*.engine"))
                            if engine_files:
                                shutil.move(str(engine_files[0]), str(engine_file))
                                logger.info(f"✅ TensorRT引擎已保存到: {engine_file}")
                            else:
                                raise FileNotFoundError(
                                    f"TensorRT转换失败: 输出文件不存在。"
                                    f"export()返回路径: {exported_path}, "
                                    f"临时目录: {tmpdir}"
                                )

                # 检查输出文件
                if engine_file.exists():
                    size_mb = engine_file.stat().st_size / (1024 * 1024)
                    logger.info(f"✅ TensorRT转换成功: {engine_file.name}")
                    logger.info(f"   文件大小: {size_mb:.2f} MB")
                    return str(engine_file)
                else:
                    logger.error("❌ TensorRT转换失败: 输出文件不存在")
                    return model_path

            return str(engine_file)

        except Exception as e:
            logger.error(f"TensorRT自动转换失败: {e}")
            logger.info("回退到PyTorch模型")
            return model_path

    def _load_model(self, model_path: str):
        """加载YOLO模型"""
        try:
            model = YOLO(model_path)

            # TensorRT 引擎文件（.engine）不支持 .to() 方法
            # 而且 TensorRT 引擎已经针对特定设备优化，不需要移动设备
            # 只有 PyTorch 模型（.pt）才需要调用 .to() 方法
            if model_path.endswith(".engine"):
                logger.info(f"成功加载TensorRT引擎: {model_path}")
            else:
                # 在测试环境中使用的 DummyYOLO 可能不实现 .to 方法，这里做兼容处理
                if hasattr(model, "to"):
                    model.to(self.device)
                logger.info(f"成功加载模型: {model_path} 到设备: {self.device}")

            return model
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            logger.info("回退到模拟模式")
            return None

    def detect(self, image: np.ndarray) -> List[Dict]:
        """
        检测图像中的人体

        Args:
            image: 输入图像 (BGR格式)

        Returns:
            检测结果列表，每个元素包含bbox、confidence、class_id等信息
        """
        if self.model is None:
            error_msg = "YOLO模型未正确加载，无法进行人体检测"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            logger.info(
                f"开始YOLO检测，图像尺寸: {image.shape}, 置信度阈值: {self.confidence_threshold}, IoU阈值: {self.iou_threshold}"
            )

            results = self.model(
                image, conf=self.confidence_threshold, iou=self.iou_threshold
            )
            detections = []
            total_boxes = 0
            filtered_boxes = 0

            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    total_boxes += len(boxes)
                    logger.info(f"YOLO原始检测到 {len(boxes)} 个目标")

                    for box in boxes:
                        # 只检测人体 (class_id = 0)
                        if int(box.cls[0]) == 0:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            confidence = float(box.conf[0].cpu().numpy())

                            # 计算检测框属性
                            width = x2 - x1
                            height = y2 - y1
                            area = width * height
                            aspect_ratio = max(width, height) / min(width, height)

                            logger.debug(
                                f"检测框: ({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}), 置信度: {confidence:.3f}, 面积: {area:.1f}, 宽高比: {aspect_ratio:.2f}"
                            )

                            # 应用后处理过滤
                            if (
                                area >= self.min_box_area
                                and aspect_ratio <= self.max_box_ratio
                                and width > self.min_width
                                and height > self.min_height
                            ):  # 使用配置的最小尺寸要求
                                detection = {
                                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                                    "confidence": confidence,
                                    "class_id": 0,
                                    "class_name": "person",
                                }
                                detections.append(detection)
                                logger.debug(f"检测框通过过滤: {detection}")
                            else:
                                filtered_boxes += 1
                                logger.debug(
                                    f"检测框被过滤: 面积={area:.1f} (最小={self.min_box_area}), 宽高比={aspect_ratio:.2f} (最大={self.max_box_ratio}), 尺寸={width:.1f}x{height:.1f}"
                                )

            logger.info(
                f"YOLO检测完成: 原始检测框={total_boxes}, 过滤后={len(detections)}, 被过滤={filtered_boxes}"
            )
            return detections

        except Exception as e:
            error_msg = f"YOLO检测过程中发生错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    def detect_batch(self, images: List[np.ndarray]) -> List[List[Dict]]:
        """
        批量检测多张图像

        Args:
            images: 图像列表

        Returns:
            每张图像的检测结果列表
        """
        results = []
        for image in images:
            detections = self.detect(image)
            results.append(detections)
        return results

    def set_confidence_threshold(self, threshold: float):
        """设置置信度阈值"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"Confidence threshold set to {self.confidence_threshold}")

    def set_iou_threshold(self, threshold: float):
        """设置IoU阈值"""
        self.iou_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"IoU threshold set to {self.iou_threshold}")

    def visualize_detections(
        self, image: np.ndarray, detections: List[Dict]
    ) -> np.ndarray:
        """
        在图像上可视化检测结果

        Args:
            image: 输入图像
            detections: 检测结果列表

        Returns:
            带有检测框的图像
        """
        return self.visualize(image, detections)
