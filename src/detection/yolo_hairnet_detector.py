#!/usr/bin/env python

"""
YOLOv8 发网检测器实现

基于 YOLOv8 的发网检测器，可以直接检测图像中的发网，无需先检测人体再提取头部区域
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import cv2
import numpy as np

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入必要的模块
try:
    from ultralytics import YOLO
except ImportError:
    logging.error("未安装 ultralytics 库，请使用 'pip install ultralytics' 安装")
    raise

# 导入统一参数配置
try:
    from src.config.unified_params import get_unified_params
except ImportError:
    # 兼容性处理
    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    from src.config.unified_params import get_unified_params

logger = logging.getLogger(__name__)


class YOLOHairnetDetector:
    """
    基于 YOLOv8 的发网检测器

    直接使用 YOLOv8 模型检测图像中的发网，无需先检测人体再提取头部区域
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "auto",
        conf_thres: Optional[float] = None,
        iou_thres: float = 0.45,
        save_debug_roi: bool = False,
        debug_roi_dir: Optional[str] = None,
    ):
        """
        初始化 YOLOv8 发网检测器

        Args:
            model_path: YOLOv8 模型路径，如果为None则使用统一配置或默认路径
            device: 计算设备，可选 'cpu', 'cuda', 'auto'
            conf_thres: 置信度阈值，如果为None则从统一配置读取
            iou_thres: IoU 阈值，默认为 0.45
            save_debug_roi: 是否保存ROI裁切内容用于调试，默认为False
            debug_roi_dir: ROI保存目录，如果为None则使用默认目录（debug/roi/）
        """
        # ROI默认参数（在读取统一配置前设置，便于在异常时使用默认值）
        self.roi_head_ratio = 0.3
        self.roi_padding_height_ratio = 0.15
        self.roi_padding_width_ratio = 0.1
        self.roi_min_size = 200
        self.roi_detection_confidence = 0.1
        self.roi_postprocess_threshold_cap = 0.2
        self.roi_min_positive_confidence = 0.1
        self.roi_expansion_pixels = 50
        self.roi_expansion_conf_scale = 0.8
        self.roi_expansion_attempts = 1

        # 获取统一参数配置
        try:
            params = get_unified_params().hairnet_detection
            # 使用统一配置的模型路径（如果未提供）
            if model_path is None:
                model_path = (
                    params.model_path or "models/hairnet_detection/hairnet_detection.pt"
                )
            # 使用统一配置的设备（如果为auto）
            if device == "auto":
                device = params.device if params.device != "auto" else "auto"
            # 使用统一配置的置信度阈值（如果未提供）
            if conf_thres is None:
                conf_thres = params.confidence_threshold
                logger.info(f"从统一配置读取置信度阈值: {conf_thres}")
            # ROI参数
            self.roi_head_ratio = getattr(params, "roi_head_ratio", self.roi_head_ratio)
            self.roi_padding_height_ratio = getattr(
                params, "roi_padding_height_ratio", self.roi_padding_height_ratio
            )
            self.roi_padding_width_ratio = getattr(
                params, "roi_padding_width_ratio", self.roi_padding_width_ratio
            )
            self.roi_min_size = getattr(params, "roi_min_size", self.roi_min_size)
            self.roi_detection_confidence = getattr(
                params, "roi_detection_confidence", self.roi_detection_confidence
            )
            self.roi_postprocess_threshold_cap = getattr(
                params,
                "roi_postprocess_threshold_cap",
                self.roi_postprocess_threshold_cap,
            )
            self.roi_min_positive_confidence = getattr(
                params, "roi_min_positive_confidence", self.roi_min_positive_confidence
            )
            self.roi_expansion_pixels = getattr(
                params, "roi_expansion_pixels", self.roi_expansion_pixels
            )
            self.roi_expansion_conf_scale = getattr(
                params, "roi_expansion_conf_scale", self.roi_expansion_conf_scale
            )
            self.roi_expansion_attempts = max(
                1,
                int(
                    getattr(
                        params, "roi_expansion_attempts", self.roi_expansion_attempts
                    )
                ),
            )
        except Exception as e:
            logger.warning(f"读取统一配置失败: {e}，使用默认值")
            if model_path is None:
                model_path = "models/hairnet_detection/hairnet_detection.pt"
            if conf_thres is None:
                conf_thres = 0.25  # 默认值

        project_root = Path(__file__).resolve().parents[2]
        if not Path(model_path).is_absolute():
            self.model_path = str(project_root / model_path)
        else:
            self.model_path = model_path

        self.device = self._get_device(device)
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        self.model = self._load_model()

        # 调试ROI保存配置
        self.save_debug_roi = save_debug_roi
        if self.save_debug_roi:
            if debug_roi_dir is None:
                project_root = Path(__file__).resolve().parents[2]
                self.debug_roi_dir = project_root / "debug" / "roi"
            else:
                self.debug_roi_dir = Path(debug_roi_dir)
            # 确保目录存在
            self.debug_roi_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"ROI调试保存已启用，保存目录: {self.debug_roi_dir}")

        logger.info(
            f"YOLOHairnetDetector初始化: conf_thres={self.conf_thres}, model_path={self.model_path}, "
            f"ROI参数: head_ratio={self.roi_head_ratio}, "
            f"padding=({self.roi_padding_width_ratio}, {self.roi_padding_height_ratio}), "
            f"min_size={self.roi_min_size}, "
            f"detection_conf={self.roi_detection_confidence}, "
            f"postprocess_cap={self.roi_postprocess_threshold_cap}, "
            f"expansion_pixels={self.roi_expansion_pixels}, "
            f"expansion_attempts={self.roi_expansion_attempts}"
        )

        # 统计信息
        self.total_detections = 0
        self.hairnet_detections = 0

        logger.info(f"YOLOHairnetDetector 初始化成功，使用设备: {self.device}")

    def _save_debug_roi(
        self,
        roi_image: np.ndarray,
        track_id: int,
        human_bbox: List[float],
        roi_coords: tuple,
        detection_result: Optional[str] = None,
        full_frame_hairnet_bbox: Optional[List[float]] = None,
    ) -> Optional[str]:
        """
        保存ROI裁切内容用于调试

        Args:
            roi_image: ROI图像
            track_id: 人员跟踪ID
            human_bbox: 人体边界框 [x1, y1, x2, y2]
            roi_coords: ROI坐标 (roi_x1, roi_y1, roi_x2, roi_y2)
            detection_result: 检测结果描述（可选），如 "detected", "not_detected", "uncertain"
            full_frame_hairnet_bbox: 全图检测到的发网bbox（可选），用于对比

        Returns:
            保存的文件路径，如果未启用保存则返回None
        """
        if not self.save_debug_roi:
            return None

        try:
            # 生成文件名：track_id_timestamp_result.jpg
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 精确到毫秒
            result_suffix = f"_{detection_result}" if detection_result else ""
            filename = f"roi_track{track_id}_{timestamp}{result_suffix}.jpg"
            filepath = self.debug_roi_dir / filename

            # 如果提供了全图检测的发网bbox，在ROI图像上绘制参考线
            roi_image_annotated = roi_image.copy()
            if full_frame_hairnet_bbox is not None:
                roi_x1, roi_y1, roi_x2, roi_y2 = roi_coords
                h_x1, h_y1, h_x2, h_y2 = full_frame_hairnet_bbox

                # 将全图坐标转换为ROI坐标
                h_roi_x1 = h_x1 - roi_x1
                h_roi_y1 = h_y1 - roi_y1
                h_roi_x2 = h_x2 - roi_x1
                h_roi_y2 = h_y2 - roi_y1

                # 检查发网bbox是否在ROI范围内
                if (
                    0 <= h_roi_x1 < roi_image.shape[1]
                    and 0 <= h_roi_y1 < roi_image.shape[0]
                    and 0 <= h_roi_x2 < roi_image.shape[1]
                    and 0 <= h_roi_y2 < roi_image.shape[0]
                ):
                    # 在ROI图像上绘制全图检测到的发网bbox（绿色虚线）
                    cv2.rectangle(
                        roi_image_annotated,
                        (int(h_roi_x1), int(h_roi_y1)),
                        (int(h_roi_x2), int(h_roi_y2)),
                        (0, 255, 0),  # 绿色
                        2,
                        cv2.LINE_AA,
                    )
                    cv2.putText(
                        roi_image_annotated,
                        f"FullFrame: {full_frame_hairnet_bbox}",
                        (int(h_roi_x1), int(h_roi_y1) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1,
                    )

            # 保存图像
            cv2.imwrite(str(filepath), roi_image_annotated)

            # 记录详细信息到日志
            logger.debug(
                f"保存ROI调试图像: track_id={track_id}, "
                f"文件={filename}, "
                f"人体bbox={human_bbox}, "
                f"ROI坐标={roi_coords}, "
                f"ROI尺寸={roi_image.shape}, "
                f"检测结果={detection_result}, "
                f"全图发网bbox={full_frame_hairnet_bbox}"
            )

            return str(filepath)
        except Exception as e:
            logger.warning(f"保存ROI调试图像失败: {e}")
            return None

    def _get_device(self, device: str) -> str:
        """
        获取计算设备

        Args:
            device: 指定的设备，'auto' 表示自动选择

        Returns:
            实际使用的设备名称
        """
        if device == "auto":
            try:
                import torch

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

    def _load_model(self):
        """
        加载 YOLOv8 模型

        Returns:
            加载的 YOLOv8 模型
        """
        try:
            if not os.path.exists(self.model_path):
                logger.warning(f"模型文件不存在: {self.model_path}，请确保已训练模型")
                raise FileNotFoundError(f"模型文件不存在: {self.model_path}")

            model = YOLO(self.model_path)
            logger.info(f"成功加载 YOLOv8 模型: {self.model_path}")
            return model
        except Exception as e:
            logger.error(f"加载 YOLOv8 模型失败: {e}")
            raise

    def detect(
        self,
        image: Union[str, np.ndarray],
        conf_thres: Optional[float] = None,
        iou_thres: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        检测图像中的发网

        Args:
            image: 输入图像路径或 numpy 数组
            conf_thres: 置信度阈值，如果为 None 则使用初始化时设置的值
            iou_thres: IoU 阈值，如果为 None 则使用初始化时设置的值

        Returns:
            检测结果字典，包含以下字段:
            - wearing_hairnet: 是否佩戴发网
            - detections: 检测到的所有目标列表，每个目标包含类别、置信度和边界框
            - visualization: 可视化结果图像
        """
        try:
            # 检查输入图像是否有效
            if image is None:
                return self._create_error_result("输入图像为空")

            if isinstance(image, str) and not os.path.exists(image):
                return self._create_error_result(f"图像文件不存在: {image}")

            if isinstance(image, np.ndarray) and image.size == 0:
                return self._create_error_result("输入图像为空数组")

            # 使用传入的阈值或默认阈值
            conf = conf_thres if conf_thres is not None else self.conf_thres
            iou = iou_thres if iou_thres is not None else self.iou_thres

            # 运行推理
            # 重要：指定imgsz=640与训练时保持一致，确保检测准确率
            results = self.model(image, conf=conf, iou=iou, imgsz=640, verbose=False)

            # 处理结果
            detections = []
            has_hairnet = False
            hairnet_confidence = 0.0

            for r in results:
                boxes = r.boxes  # 边界框
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()  # 边界框坐标
                    conf = float(box.conf[0])  # 置信度
                    cls = int(box.cls[0])  # 类别
                    cls_name = self.model.names[cls]  # 类别名称

                    # 确保所有值都是Python原生类型，可以被JSON序列化
                    detection = {
                        "class": str(cls_name),
                        "confidence": float(conf),
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    }
                    detections.append(detection)

                    # 检查是否为发网类别
                    if cls_name.lower() == "hairnet" and conf > hairnet_confidence:
                        has_hairnet = True
                        hairnet_confidence = conf

            # 更新统计信息
            self.total_detections += 1
            if has_hairnet:
                self.hairnet_detections += 1

            # 创建结果
            # 注意：visualization是numpy数组，需要转换为可序列化的格式
            visualization = results[0].plot() if results else None

            result = {
                "wearing_hairnet": has_hairnet,
                "has_hairnet": has_hairnet,  # 兼容旧接口
                "confidence": float(hairnet_confidence),  # 确保是Python原生float类型
                "detections": detections,
                "visualization": visualization,  # 这里visualization仍然是numpy数组，但在API返回前会被转换为base64
                "error": None,
            }

            logger.info(
                f"发网检测结果: 佩戴={has_hairnet}, 置信度={hairnet_confidence:.3f}, 检测到的目标数量={len(detections)}"
            )
            return result

        except Exception as e:
            logger.error(f"发网检测失败: {e}")
            return self._create_error_result(str(e))

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """
        创建错误结果

        Args:
            error_message: 错误信息

        Returns:
            错误结果字典
        """
        return {
            "wearing_hairnet": False,
            "has_hairnet": False,
            "confidence": 0.0,
            "detections": [],
            "visualization": None,
            "error": error_message,
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        获取检测统计信息

        Returns:
            统计信息字典
        """
        hairnet_rate = 0.0
        if self.total_detections > 0:
            hairnet_rate = self.hairnet_detections / self.total_detections

        return {
            "total_detections": int(self.total_detections),  # 确保是Python原生int类型
            "hairnet_detections": int(self.hairnet_detections),  # 确保是Python原生int类型
            "hairnet_rate": float(hairnet_rate),  # 确保是Python原生float类型
        }

    def reset_stats(self):
        """
        重置统计信息
        """
        self.total_detections = 0
        self.hairnet_detections = 0
        logger.info("统计信息已重置")

    def detect_hairnet_compliance(
        self,
        image: Union[str, np.ndarray],
        human_detections: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        检测图像中的发网佩戴合规性（与传统检测器API兼容）

        Args:
            image: 输入图像
            human_detections: 可选的人体检测结果，如果提供则不会重复进行人体检测

        Returns:
            dict: 包含检测结果的字典，格式与传统检测器兼容
        """
        logger.warning(
            f"🔵 进入detect_hairnet_compliance: "
            f"human_detections={'提供' if human_detections else '未提供'}, "
            f"数量={len(human_detections) if human_detections else 0}"
        )
        try:
            # 如果没有提供人体检测结果，则进行人体检测
            if human_detections is None:
                try:
                    from src.detection.detector import HumanDetector

                    human_detector = HumanDetector()
                    human_detections = human_detector.detect(image)
                    logger.info(f"人体检测结果: 检测到 {len(human_detections)} 个人")
                except Exception as e:
                    logger.warning(f"人体检测失败，使用发网检测结果: {e}")
                    human_detections = []
            else:
                logger.warning(f"🔵 使用提供的人体检测结果: 检测到 {len(human_detections)} 个人")

            # 确保图像是numpy数组格式
            if isinstance(image, str):
                image_array = cv2.imread(image)
                if image_array is None:
                    raise ValueError(f"无法读取图像文件: {image}")
            else:
                image_array = image

            logger.warning(
                f"🔵 准备检测: human_detections={'存在' if human_detections else '不存在'}, "
                f"数量={len(human_detections) if human_detections else 0}, "
                f"图像大小={image_array.shape}"
            )

            # 优化：如果提供了人体检测结果，先尝试全图检测（因为全图检测更可靠）
            # 如果全图检测失败，再使用ROI检测
            if human_detections and len(human_detections) > 0:
                # 策略：先尝试全图检测（更可靠），如果失败再使用ROI检测
                logger.warning(
                    f"🔵 检测策略: 先尝试全图检测，人数={len(human_detections)}, "
                    f"图像大小={image_array.shape}"
                )

                # 先进行全图检测（降低置信度阈值以提高召回率）
                full_frame_result = self.detect(image_array, conf_thres=0.05)  # type: ignore
                full_frame_detections = full_frame_result.get("detections", [])
                full_frame_has_hairnet = full_frame_result.get("wearing_hairnet", False)
                full_frame_confidence = full_frame_result.get("confidence", 0.0)

                # 提取全图检测到的发网bbox
                hairnet_bboxes = []
                for det in full_frame_detections:
                    det_class = det.get("class", "").lower()
                    det_bbox = det.get("bbox", [])
                    if det_class == "hairnet":
                        hairnet_bboxes.append(det_bbox)
                        logger.warning(
                            f"🔵 提取到发网bbox: class={det_class}, "
                            f"bbox={det_bbox}, confidence={det.get('confidence', 0.0):.3f}"
                        )

                logger.warning(
                    f"🔵 全图检测结果: 检测到={len(full_frame_detections)}个目标, "
                    f"有发网={full_frame_has_hairnet}, 置信度={full_frame_confidence:.3f}, "
                    f"发网bbox数量={len(hairnet_bboxes)}"
                )

                # 如果全图检测成功，直接使用全图检测结果
                if full_frame_has_hairnet and full_frame_confidence >= 0.1:
                    logger.warning(
                        f"🔵 ✅ 全图检测成功，直接使用全图检测结果: " f"置信度={full_frame_confidence:.3f}"
                    )
                    # 将全图检测结果映射到每个人
                    persons_with_hairnet = 0
                    updated_detections = []

                    logger.warning(
                        f"🔵 开始映射全图检测结果到人员: 人数={len(human_detections)}, "
                        f"发网bbox数量={len(hairnet_bboxes)}"
                    )

                    for i, human_det in enumerate(human_detections):
                        human_bbox = human_det.get("bbox", [0, 0, 0, 0])
                        track_id = human_det.get("track_id", i)
                        # 检查是否有发网bbox与这个人体bbox重叠
                        has_hairnet_for_person = False
                        best_hairnet_confidence = 0.0

                        logger.warning(
                            f"🔵 检查人员 {i+1} (track_id={track_id}): "
                            f"人体bbox={human_bbox}"
                        )

                        for j, hairnet_bbox in enumerate(hairnet_bboxes):
                            h_x1, h_y1, h_x2, h_y2 = hairnet_bbox
                            p_x1, p_y1, p_x2, p_y2 = human_bbox

                            # 检查发网bbox是否与人体bbox重叠
                            overlaps = not (
                                h_x2 < p_x1 or h_x1 > p_x2 or h_y2 < p_y1 or h_y1 > p_y2
                            )

                            logger.warning(
                                f"🔵   发网bbox {j+1}: {hairnet_bbox}, "
                                f"与人体bbox重叠={overlaps}"
                            )

                            if overlaps:
                                has_hairnet_for_person = True
                                # 从全图检测结果中找到对应的置信度
                                for det in full_frame_detections:
                                    det_bbox = det.get("bbox", [])
                                    # 使用更宽松的匹配：检查bbox是否近似相等（允许小的浮点误差）
                                    if len(det_bbox) == 4 and len(hairnet_bbox) == 4:
                                        bbox_match = all(
                                            abs(det_bbox[k] - hairnet_bbox[k]) < 1.0
                                            for k in range(4)
                                        )
                                        if bbox_match:
                                            conf = det.get("confidence", 0.0)
                                            if conf > best_hairnet_confidence:
                                                best_hairnet_confidence = conf
                                                logger.warning(
                                                    f"🔵     匹配到发网: 置信度={conf:.3f}, "
                                                    f"bbox={hairnet_bbox}"
                                                )

                        if has_hairnet_for_person:
                            persons_with_hairnet += 1
                            logger.warning(
                                f"🔵 ✅ 人员 {i+1} (track_id={track_id}) 检测到发网: "
                                f"置信度={best_hairnet_confidence:.3f}"
                            )
                        else:
                            logger.warning(f"🔵 ❌ 人员 {i+1} (track_id={track_id}) 未检测到发网")

                        updated_detections.append(
                            {
                                "bbox": human_bbox,
                                "has_hairnet": has_hairnet_for_person,
                                "confidence": human_det.get("confidence", 1.0),
                                "hairnet_confidence": best_hairnet_confidence,
                            }
                        )

                    logger.warning(
                        f"🔵 映射完成: persons_with_hairnet={persons_with_hairnet}, "
                        f"总人数={len(human_detections)}"
                    )

                    # 如果还有人员未匹配到发网，使用ROI检测作为补充
                    if persons_with_hairnet < len(human_detections):
                        unmatched_persons = [
                            (i, det)
                            for i, det in enumerate(updated_detections)
                            if not det.get("has_hairnet", False)
                        ]

                        if unmatched_persons:
                            logger.warning(
                                f"🔵 {len(unmatched_persons)} 个人员未在全图检测中匹配到发网，"
                                f"尝试ROI检测补充: track_ids={[human_detections[i].get('track_id', i) for i, _ in unmatched_persons]}"
                            )

                            # 对未匹配的人员进行ROI检测
                            unmatched_human_detections = [
                                human_detections[i] for i, _ in unmatched_persons
                            ]
                            roi_result = self._detect_hairnet_in_rois(
                                image_array, unmatched_human_detections
                            )

                            # 更新未匹配人员的检测结果
                            roi_detections = roi_result.get("detections", [])
                            for idx, (i, _) in enumerate(unmatched_persons):
                                if idx < len(roi_detections):
                                    roi_det = roi_detections[idx]
                                    roi_has_hairnet = roi_det.get("has_hairnet", False)
                                    roi_confidence = roi_det.get(
                                        "hairnet_confidence", 0.0
                                    )

                                    if (
                                        roi_has_hairnet
                                        and roi_confidence
                                        >= self.roi_min_positive_confidence
                                    ):
                                        # ROI检测到发网，更新结果
                                        updated_detections[i]["has_hairnet"] = True
                                        updated_detections[i][
                                            "hairnet_confidence"
                                        ] = roi_confidence
                                        persons_with_hairnet += 1

                                        track_id = human_detections[i].get(
                                            "track_id", i
                                        )
                                        logger.warning(
                                            f"🔵 ✅ ROI检测补充: 人员 {i+1} (track_id={track_id}) "
                                            f"检测到发网，置信度={roi_confidence:.3f}"
                                        )

                    result = {
                        "total_persons": len(human_detections),
                        "persons_with_hairnet": persons_with_hairnet,
                        "persons_without_hairnet": len(human_detections)
                        - persons_with_hairnet,
                        "compliance_rate": (
                            persons_with_hairnet / len(human_detections)
                        )
                        if len(human_detections) > 0
                        else 0.0,
                        "detections": updated_detections,
                        "average_confidence": full_frame_confidence,
                        "error": None,
                    }

                    # 全图检测成功（可能配合ROI补充），返回结果
                    logger.warning(
                        f"🔵 全图检测完成（可能配合ROI补充），返回结果: "
                        f"persons_with_hairnet={result['persons_with_hairnet']}, "
                        f"total_persons={result['total_persons']}"
                    )
                    return result
                else:
                    # 全图检测失败，回退到ROI检测
                    logger.warning(
                        f"⚠️ 全图检测未检测到发网，回退到ROI检测: "
                        f"有发网={full_frame_has_hairnet}, 置信度={full_frame_confidence:.3f}"
                    )
                    result = self._detect_hairnet_in_rois(image_array, human_detections)

                    # 诊断：如果ROI检测失败，分析原因
                    if result.get("persons_with_hairnet", 0) == 0:
                        logger.warning(
                            f"⚠️ ROI检测失败，分析原因: "
                            f"人数={len(human_detections)}, "
                            f"全图检测结果={full_frame_has_hairnet}, "
                            f"全图置信度={full_frame_confidence:.3f}"
                        )

                        # 诊断：对比全图检测到的发网位置和ROI提取位置
                        if hairnet_bboxes and result.get("detections"):
                            logger.warning("🔍 诊断：对比全图检测和ROI检测的位置")
                            for det in result.get("detections", []):
                                human_bbox = det.get("bbox", [])
                                p_x1, p_y1, p_x2, p_y2 = human_bbox
                                person_height = p_y2 - p_y1
                                person_width = p_x2 - p_x1

                                # 计算ROI区域（与提取时保持一致）
                                head_height = int(person_height * 0.30)
                                padding_height = int(head_height * 0.15)
                                padding_width = int(person_width * 0.10)
                                roi_x1 = max(0, p_x1 - padding_width)
                                roi_y1 = max(0, p_y1 - padding_height)
                                roi_x2 = min(image_array.shape[1], p_x2 + padding_width)
                                roi_y2 = min(
                                    image_array.shape[0],
                                    p_y1 + head_height + padding_height,
                                )

                                logger.warning(
                                    f"  人体bbox={human_bbox}, "
                                    f"计算的ROI区域=({roi_x1}, {roi_y1}, {roi_x2}, {roi_y2}), "
                                    f"全图检测到的发网bbox={hairnet_bboxes}"
                                )

                                # 检查每个发网bbox是否在ROI区域内
                                for hairnet_bbox in hairnet_bboxes:
                                    h_x1, h_y1, h_x2, h_y2 = hairnet_bbox

                                    # 计算发网中心点
                                    h_center_x = (h_x1 + h_x2) / 2
                                    h_center_y = (h_y1 + h_y2) / 2

                                    # 检查发网中心是否在ROI内
                                    center_in_roi = (
                                        roi_x1 <= h_center_x <= roi_x2
                                        and roi_y1 <= h_center_y <= roi_y2
                                    )

                                    logger.warning(
                                        f"    发网bbox={hairnet_bbox}, "
                                        f"发网中心=({h_center_x:.0f}, {h_center_y:.0f}), "
                                        f"ROI区域=({roi_x1}, {roi_y1}, {roi_x2}, {roi_y2}), "
                                        f"发网中心在ROI内={center_in_roi}"
                                    )

                                    # 如果发网不在ROI内，说明ROI提取位置有问题
                                    if not center_in_roi:
                                        logger.warning(
                                            "    ⚠️ 问题：全图检测到的发网位置不在ROI区域内！"
                                            "这可能说明ROI提取位置不准确，或者发网位置超出了预期的头部区域。"
                                        )
            else:
                # 回退到全帧检测
                logger.info(f"没有人体检测结果，使用全帧检测: 图像大小={image_array.shape}")
                result = self.detect(image_array)  # type: ignore

            if result.get("error"):
                # 如果检测失败，返回默认结果
                return {
                    "total_persons": len(human_detections),
                    "persons_with_hairnet": 0,
                    "persons_without_hairnet": len(human_detections),
                    "compliance_rate": 0.0,
                    "detections": [],
                    "average_confidence": 0.0,
                    "error": result["error"],
                }

            # 处理检测结果
            hairnet_detections = result.get("detections", [])

            # 统计发网检测结果
            total_persons = len(human_detections)
            persons_with_hairnet = 0
            persons_without_hairnet = 0
            compliance_detections = []

            # 如果有人体检测结果，为每个人创建检测记录
            if human_detections:
                # 检查是否有发网检测结果
                # 如果有发网检测结果，则进行重叠检测
                # 如果没有发网检测结果，则认为检测结果不明确，不判定为违规
                has_hairnet_detections = len(hairnet_detections) > 0

                for i, human_det in enumerate(human_detections):
                    human_bbox = human_det.get("bbox", [0, 0, 0, 0])
                    human_confidence = human_det.get("confidence", 0.0)

                    # 检查该人是否佩戴发网（通过检查发网检测框是否与人体框重叠）
                    has_hairnet = None  # None 表示检测结果不明确
                    hairnet_confidence = 0.0

                    # 只有在有发网检测结果时，才进行判断
                    if has_hairnet_detections:
                        for hairnet_det in hairnet_detections:
                            if hairnet_det.get("class", "").lower() == "hairnet":
                                hairnet_bbox = hairnet_det.get("bbox", [0, 0, 0, 0])
                                hairnet_conf = hairnet_det.get("confidence", 0.0)
                                # 简单的重叠检测：如果发网框与人体框有重叠，认为该人佩戴发网
                                if self._boxes_overlap(human_bbox, hairnet_bbox):
                                    has_hairnet = True
                                    hairnet_confidence = hairnet_conf
                                    break

                        # 如果检测到发网但没有重叠，则明确判定为未佩戴发网
                        if has_hairnet is None:
                            has_hairnet = False
                            # 使用最高置信度的发网检测结果作为参考
                            hairnet_detections_filtered = [
                                det.get("confidence", 0.0)
                                for det in hairnet_detections
                                if det.get("class", "").lower() == "hairnet"
                            ]
                            if hairnet_detections_filtered:
                                hairnet_confidence = max(hairnet_detections_filtered)
                            else:
                                hairnet_confidence = 0.0
                    else:
                        # 如果没有发网检测结果，则认为检测结果不明确
                        # 不判定为违规，避免误判
                        logger.debug(
                            f"发网检测模型未检测到发网，检测结果不明确: "
                            f"human_bbox={human_bbox}, confidence={human_confidence}"
                        )

                    if has_hairnet is True:
                        persons_with_hairnet += 1
                    elif has_hairnet is False:
                        persons_without_hairnet += 1
                    # 如果 has_hairnet 为 None，则不计入统计，避免误判

                    # 构建兼容格式的检测结果
                    compliance_detections.append(
                        {
                            "bbox": human_bbox,
                            "has_hairnet": has_hairnet,  # 可能是 True、False 或 None
                            "confidence": human_confidence,
                            "hairnet_confidence": hairnet_confidence,
                        }
                    )
            else:
                # 如果没有人体检测结果，但有发网检测结果，假设每个发网对应一个人
                for hairnet_det in hairnet_detections:
                    if hairnet_det.get("class", "").lower() == "hairnet":
                        total_persons += 1
                        persons_with_hairnet += 1

                        compliance_detections.append(
                            {
                                "bbox": hairnet_det.get("bbox", [0, 0, 0, 0]),
                                "has_hairnet": True,
                                "confidence": hairnet_det.get("confidence", 0.0),
                                "hairnet_confidence": hairnet_det.get(
                                    "confidence", 0.0
                                ),
                            }
                        )

            # 计算合规率
            compliance_rate = (
                (persons_with_hairnet / total_persons) if total_persons > 0 else 0.0
            )

            # 计算平均置信度
            if compliance_detections:
                average_confidence = sum(
                    det["confidence"] for det in compliance_detections
                ) / len(compliance_detections)
            else:
                average_confidence = 0.0

            logger.info(
                f"发网合规性检测结果: 总人数={total_persons}, 佩戴发网={persons_with_hairnet}, 未佩戴={persons_without_hairnet}, 合规率={compliance_rate:.2f}"
            )

            return {
                "total_persons": total_persons,
                "persons_with_hairnet": persons_with_hairnet,
                "persons_without_hairnet": persons_without_hairnet,
                "compliance_rate": compliance_rate,
                "detections": compliance_detections,
                "average_confidence": average_confidence,
            }

        except Exception as e:
            logger.error(f"发网合规性检测失败: {e}")
            return {
                "total_persons": 0,
                "persons_with_hairnet": 0,
                "persons_without_hairnet": 0,
                "compliance_rate": 0.0,
                "detections": [],
                "average_confidence": 0.0,
                "error": str(e),
            }

    def _detect_hairnet_in_rois(
        self,
        image: np.ndarray,
        human_detections: List[Dict],
        use_batch: bool = True,  # 任务3.3：是否使用批量检测
    ) -> Dict[str, Any]:
        """
        在头部ROI区域进行发网检测（任务3.1：ROI优化 + 任务3.3：批量优化）

        Args:
            image: 完整图像
            human_detections: 人体检测结果列表
            use_batch: 是否使用批量检测（任务3.3）

        Returns:
            检测结果字典（兼容detect_hairnet_compliance格式）
        """
        try:
            # 任务3.3：如果启用批量检测且有多个人，使用批量检测
            if use_batch and len(human_detections) > 1:
                return self._batch_detect_hairnet_in_rois(image, human_detections)

            # 否则使用逐个检测（原有逻辑）
            compliance_detections = []
            persons_with_hairnet = 0
            persons_without_hairnet = 0
            all_detections = []

            # 对每个人进行头部ROI检测
            for i, human_det in enumerate(human_detections):
                human_bbox = human_det.get("bbox", [0, 0, 0, 0])
                track_id = human_det.get("track_id", i)
                human_confidence = human_det.get("confidence", 1.0)

                # 提取头部ROI（优化：从35%增加到45%，提高头部区域覆盖率）
                # 全图检测成功说明模型正常，ROI可能太小或位置不准确
                x1, y1, x2, y2 = map(int, human_bbox)
                person_height = y2 - y1
                person_width = x2 - x1

                # 优化：使用配置化的头部区域比例，只包含头部和发网
                head_height = int(person_height * self.roi_head_ratio)

                # 确保ROI有效
                if x2 <= x1 or y2 <= y1 or head_height <= 0:
                    logger.warning(f"无效的人体边界框: {human_bbox}")
                    continue

                # 优化：使用配置化的padding，确保包含发网边缘但不超出太多
                padding_height = int(head_height * self.roi_padding_height_ratio)
                padding_width = int(person_width * self.roi_padding_width_ratio)

                roi_x1 = max(0, x1 - padding_width)
                roi_y1 = max(0, y1 - padding_height)  # 向上扩展，包含头顶
                roi_x2 = min(image.shape[1], x2 + padding_width)
                roi_y2 = min(image.shape[0], y1 + head_height + padding_height)  # 向下扩展

                head_roi = image[roi_y1:roi_y2, roi_x1:roi_x2]

                if head_roi.size == 0:
                    logger.warning(f"头部ROI为空: {human_bbox}")
                    continue

                # 诊断日志：记录ROI提取的详细信息
                roi_width, roi_height = head_roi.shape[1], head_roi.shape[0]
                min_roi_size = self.roi_min_size  # 最小ROI尺寸阈值（可配置）
                is_small_roi = roi_width < min_roi_size or roi_height < min_roi_size

                logger.warning(
                    f"📊 ROI提取详情（单个）: track_id={track_id}, "
                    f"人体bbox=({x1}, {y1}, {x2}, {y2}), "
                    f"人体尺寸=({person_width}, {person_height}), "
                    f"头部高度={head_height} ({self.roi_head_ratio*100:.0f}% of person_height), "
                    f"ROI区域=({roi_x1}, {roi_y1}, {roi_x2}, {roi_y2}), "
                    f"ROI尺寸={head_roi.shape} ({roi_width}x{roi_height}), "
                    f"padding=({padding_width}, {padding_height}), "
                    f"是否小ROI={is_small_roi} (最小阈值={min_roi_size}), "
                    f"配置参数: head_ratio={self.roi_head_ratio}, "
                    f"padding_h={self.roi_padding_height_ratio}, padding_w={self.roi_padding_width_ratio}"
                )

                # 保存ROI用于调试（如果启用）
                if self.save_debug_roi:
                    self._save_debug_roi(
                        head_roi,
                        track_id,
                        human_bbox,
                        (roi_x1, roi_y1, roi_x2, roi_y2),
                        detection_result="before_detection",
                    )

                # 注意：预处理（CLAHE + 锐化）会改变图像特征，导致模型无法识别
                # 测试发现：不使用预处理可以正常检测到发网，使用预处理后检测失败
                # 因此暂时禁用预处理，直接使用原始ROI
                # 如果后续需要预处理，可以添加开关控制或降低预处理强度
                # try:
                #     # 转换为LAB颜色空间进行亮度增强
                #     lab = cv2.cvtColor(head_roi, cv2.COLOR_BGR2LAB)
                #     l, a, b = cv2.split(lab)
                #     clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                #     l_enhanced = clahe.apply(l)
                #     lab_enhanced = cv2.merge([l_enhanced, a, b])
                #     head_roi = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
                #     kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]]) * 0.1
                #     head_roi = cv2.filter2D(head_roi, -1, kernel)
                # except Exception as e:
                #     logger.debug(f"ROI预处理失败，使用原始ROI: {e}")

                # 在ROI上运行发网检测
                # 优化：使用配置化的检测阈值，以提高检测敏感度
                detection_conf = self.roi_detection_confidence
                iou = self.iou_thres

                logger.debug(
                    f"开始发网检测: human_bbox={human_bbox}, "
                    f"ROI大小={head_roi.shape}, "
                    f"检测阈值={detection_conf}, "
                    f"配置阈值={self.conf_thres}"
                )

                try:
                    # 使用低阈值进行检测，捕获更多可能的发网
                    # 重要：指定imgsz=640与训练时保持一致，确保检测准确率
                    logger.warning(
                        f"🔍 开始ROI模型推理（单个）: track_id={track_id}, "
                        f"ROI大小={head_roi.shape}, "
                        f"ROI尺寸=({roi_width}x{roi_height}), "
                        f"检测阈值={detection_conf}, "
                        f"模型输入尺寸=640x640 (自动resize)"
                    )
                    results = self.model(
                        head_roi, conf=detection_conf, iou=iou, imgsz=640, verbose=False
                    )

                    # 详细诊断：输出模型原始结果
                    total_boxes = 0
                    all_raw_detections = []
                    for r in results:
                        boxes = r.boxes
                        if boxes is not None:
                            total_boxes += len(boxes)
                            for box in boxes:
                                conf = float(box.conf[0])
                                cls = int(box.cls[0])
                                cls_name = self.model.names[cls]
                                all_raw_detections.append(
                                    {
                                        "class": cls_name,
                                        "confidence": conf,
                                        "bbox": box.xyxy[0].cpu().numpy().tolist(),
                                    }
                                )

                    logger.warning(
                        f"✅ ROI模型推理完成（单个）: track_id={track_id}, "
                        f"结果数量={len(results)}, "
                        f"检测框总数={total_boxes}, "
                        f"ROI大小={head_roi.shape}, "
                        f"检测阈值={detection_conf}, "
                        f"原始检测结果={all_raw_detections}"
                    )
                except Exception as e:
                    logger.error(
                        f"ROI发网检测失败: human_bbox={human_bbox}, track_id={track_id}, "
                        f"ROI大小={head_roi.shape}, error={e}",
                        exc_info=True,
                    )
                    continue

                # 处理检测结果
                has_hairnet = None  # None表示检测结果不明确
                hairnet_confidence = 0.0
                roi_detections = []
                all_classes_found = []  # 记录所有检测到的类别

                # 遍历所有检测结果
                for r in results:
                    boxes = r.boxes
                    num_boxes = len(boxes) if boxes is not None else 0

                    if boxes is None or num_boxes == 0:
                        logger.debug(
                            f"检测结果为空: track_id={track_id}, " f"ROI大小={head_roi.shape}"
                        )
                        continue

                    logger.info(
                        f"检测结果: track_id={track_id}, "
                        f"检测到 {num_boxes} 个目标, "
                        f"ROI大小={head_roi.shape}, "
                        f"human_bbox={human_bbox}"
                    )

                    # 处理每个检测到的目标
                    for box in boxes:
                        # ROI内的坐标
                        roi_x1_det, roi_y1_det, roi_x2_det, roi_y2_det = (
                            box.xyxy[0].cpu().numpy()
                        )
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        cls_name = self.model.names[cls]
                        all_classes_found.append((cls_name, conf))

                        logger.debug(
                            f"检测到目标: class={cls_name}, confidence={conf:.3f}, "
                            f"bbox=[{roi_x1_det:.1f}, {roi_y1_det:.1f}, {roi_x2_det:.1f}, {roi_y2_det:.1f}]"
                        )

                        # 映射回原图坐标
                        orig_x1 = float(roi_x1 + roi_x1_det)
                        orig_y1 = float(roi_y1 + roi_y1_det)
                        orig_x2 = float(roi_x1 + roi_x2_det)
                        orig_y2 = float(roi_y1 + roi_y2_det)

                        detection = {
                            "class": str(cls_name),
                            "confidence": float(conf),
                            "bbox": [orig_x1, orig_y1, orig_x2, orig_y2],
                        }
                        roi_detections.append(detection)
                        all_detections.append(detection)

                        # 检查是否为发网类别
                        if cls_name.lower() == "hairnet":
                            # 优化：记录所有发网检测结果，使用最高置信度
                            if has_hairnet is None:
                                has_hairnet = True
                                hairnet_confidence = conf
                                logger.info(
                                    f"✅ 检测到发网: confidence={conf:.3f}, "
                                    f"human_bbox={human_bbox}, track_id={track_id}, "
                                    f"ROI大小={head_roi.shape}"
                                )
                            elif conf > hairnet_confidence:
                                hairnet_confidence = conf
                                logger.info(
                                    f"✅ 更新发网置信度: confidence={conf:.3f}, "
                                    f"human_bbox={human_bbox}, track_id={track_id}, "
                                    f"ROI大小={head_roi.shape}"
                                )

                # 记录所有检测到的类别（用于调试）
                if all_classes_found:
                    logger.info(
                        f"检测到的所有类别: {all_classes_found}, "
                        f"human_bbox={human_bbox}, track_id={track_id}, "
                        f"ROI大小={head_roi.shape}"
                    )
                else:
                    logger.warning(
                        f"⚠️ ROI检测未检测到任何目标: human_bbox={human_bbox}, "
                        f"track_id={track_id}, ROI大小={head_roi.shape}, "
                        f"检测阈值={detection_conf}, "
                        f"ROI范围=({roi_x1}, {roi_y1}) -> ({roi_x2}, {roi_y2})"
                    )

                # 备用策略：如果未检测到发网（has_hairnet为None或False），尝试扩展ROI检测
                # 无论是否检测到其他类别，只要没有检测到发网，就尝试扩展ROI
                logger.warning(
                    f"检查扩展ROI检测条件（单个）: track_id={track_id}, "
                    f"has_hairnet={has_hairnet}, "
                    f"type={type(has_hairnet)}, "
                    f"is None={has_hairnet is None}, "
                    f"is False={has_hairnet is False}"
                )
                if has_hairnet is None or has_hairnet is False:
                    logger.warning(
                        f"✅ 触发扩展ROI检测（单个）: track_id={track_id}, "
                        f"has_hairnet={has_hairnet}"
                    )
                    # 多次尝试扩展ROI（根据配置）
                    for attempt in range(self.roi_expansion_attempts):
                        expansion = self.roi_expansion_pixels * (attempt + 1)
                        expanded_roi_x1 = max(0, roi_x1 - expansion)
                        expanded_roi_y1 = max(0, roi_y1 - expansion)
                        expanded_roi_x2 = min(image.shape[1], roi_x2 + expansion)
                        expanded_roi_y2 = min(image.shape[0], roi_y2 + expansion)
                        expanded_roi = image[
                            expanded_roi_y1:expanded_roi_y2,
                            expanded_roi_x1:expanded_roi_x2,
                        ]

                        logger.warning(
                            f"扩展ROI提取（单个）: track_id={track_id}, "
                            f"尝试={attempt + 1}/{self.roi_expansion_attempts}, "
                            f"原始ROI=({roi_x1}, {roi_y1}, {roi_x2}, {roi_y2}), "
                            f"扩展ROI=({expanded_roi_x1}, {expanded_roi_y1}, {expanded_roi_x2}, {expanded_roi_y2}), "
                            f"扩展ROI大小={expanded_roi.shape if expanded_roi.size > 0 else '空'}"
                        )

                        if expanded_roi.size == 0:
                            continue

                        logger.warning(
                            f"🔍 尝试扩展ROI检测（单个）: track_id={track_id}, "
                            f"扩展ROI大小={expanded_roi.shape}, "
                            f"原因={'未检测到任何目标' if not all_classes_found else '未检测到发网'}"
                        )
                        try:
                            expanded_conf = max(
                                self.roi_min_positive_confidence,
                                detection_conf * self.roi_expansion_conf_scale,
                            )
                            logger.warning(
                                f"开始扩展ROI模型推理（单个）: track_id={track_id}, "
                                f"尝试={attempt + 1}/{self.roi_expansion_attempts}, "
                                f"扩展ROI大小={expanded_roi.shape}, "
                                f"扩展像素={expansion}, "
                                f"检测阈值={expanded_conf}, "
                                f"模型输入尺寸=640x640 (自动resize)"
                            )

                            # 保存扩展ROI用于调试
                            if self.save_debug_roi:
                                self._save_debug_roi(
                                    expanded_roi,
                                    track_id,
                                    human_bbox,
                                    (
                                        expanded_roi_x1,
                                        expanded_roi_y1,
                                        expanded_roi_x2,
                                        expanded_roi_y2,
                                    ),
                                    detection_result=f"expanded_attempt_{attempt + 1}",
                                )

                            expanded_results = self.model(
                                expanded_roi,
                                conf=expanded_conf,
                                iou=iou,
                                imgsz=640,
                                verbose=False,
                            )

                            logger.warning(
                                f"扩展ROI模型推理完成（单个）: track_id={track_id}, "
                                f"尝试={attempt + 1}/{self.roi_expansion_attempts}, "
                                f"结果数量={len(expanded_results)}"
                            )

                            expanded_detections = []
                            for r_idx, r in enumerate(expanded_results):
                                boxes = r.boxes
                                num_boxes = len(boxes) if boxes is not None else 0
                                logger.warning(
                                    f"扩展ROI结果 {r_idx}（单个）: track_id={track_id}, "
                                    f"检测框数量={num_boxes}"
                                )
                                if boxes is not None:
                                    for box_idx, box in enumerate(boxes):
                                        cls = int(box.cls[0])
                                        cls_name = self.model.names[cls]
                                        conf = float(box.conf[0])
                                        expanded_detections.append((cls_name, conf))

                                        if cls_name.lower() == "hairnet":
                                            # 检查检测框是否在原始ROI附近
                                            box_x1, box_y1, box_x2, box_y2 = (
                                                box.xyxy[0].cpu().numpy()
                                            )
                                            box_center_x = (
                                                box_x1 + box_x2
                                            ) / 2 + expanded_roi_x1
                                            box_center_y = (
                                                box_y1 + box_y2
                                            ) / 2 + expanded_roi_y1

                                            logger.warning(
                                                f"扩展ROI检测到hairnet类别（单个）: track_id={track_id}, "
                                                f"confidence={conf:.3f}, "
                                                f"位置=({box_center_x:.0f}, {box_center_y:.0f}), "
                                                f"原始ROI=({roi_x1}, {roi_y1}, {roi_x2}, {roi_y2})"
                                            )

                                            # 如果检测框中心在原始ROI附近（按扩展像素内），认为有效
                                            if (
                                                roi_x1 - expansion
                                                <= box_center_x
                                                <= roi_x2 + expansion
                                                and roi_y1 - expansion
                                                <= box_center_y
                                                <= roi_y2 + expansion
                                            ):
                                                has_hairnet = True
                                                hairnet_confidence = max(
                                                    hairnet_confidence, conf
                                                )
                                                logger.warning(
                                                    f"✅ 扩展ROI检测到发网（单个）: track_id={track_id}, "
                                                    f"confidence={conf:.3f}, "
                                                    f"位置在原始ROI附近"
                                                )
                                            else:
                                                logger.warning(
                                                    f"⚠️ 扩展ROI检测到发网但位置不在原始ROI附近（单个）: "
                                                    f"track_id={track_id}, confidence={conf:.3f}, "
                                                    f"位置=({box_center_x:.0f}, {box_center_y:.0f}), "
                                                    f"原始ROI范围=({roi_x1-expansion}, {roi_y1-expansion}) "
                                                    f"-> ({roi_x2+expansion}, {roi_y2+expansion})"
                                                )

                            if expanded_detections:
                                logger.warning(
                                    f"扩展ROI检测结果（单个）: track_id={track_id}, "
                                    f"检测到的类别={expanded_detections}"
                                )
                            else:
                                logger.warning(
                                    f"扩展ROI检测未检测到任何目标（单个）: track_id={track_id}, "
                                    f"扩展ROI大小={expanded_roi.shape}, "
                                    f"检测阈值={expanded_conf}"
                                )

                            # 如果成功检测到发网则停止进一步扩展
                            if has_hairnet:
                                break
                        except Exception as e:
                            logger.warning(
                                f"扩展ROI检测失败（单个）: track_id={track_id}, 尝试={attempt + 1}, error={e}",
                                exc_info=True,
                            )

                    if has_hairnet is None:
                        has_hairnet = None
                        hairnet_confidence = 0.0

                # 优化：改进发网佩戴状态判断逻辑
                # 1. 如果检测到发网，使用更宽松的阈值进行最终判断
                # 2. 如果置信度 >= 0.15，就标记为佩戴（降低阈值要求，提高敏感度）
                # 3. 只有在完全检测不到发网时才标记为"不确定"
                if has_hairnet is True:
                    # 检测到发网，使用更宽松的阈值进行最终判断
                    # 进一步降低后处理阈值要求，提高检测敏感度
                    post_process_threshold = min(
                        self.conf_thres, self.roi_postprocess_threshold_cap
                    )

                    if hairnet_confidence >= post_process_threshold:
                        # 置信度足够，确认佩戴发网
                        persons_with_hairnet += 1
                        logger.info(
                            f"✅ 确认佩戴发网: human_bbox={human_bbox}, track_id={track_id}, "
                            f"hairnet_confidence={hairnet_confidence:.3f}, "
                            f"post_process_threshold={post_process_threshold:.3f}"
                        )
                    elif hairnet_confidence >= self.roi_min_positive_confidence:
                        # 置信度较低但仍有检测结果，标记为"可能佩戴"
                        persons_with_hairnet += 1
                        logger.warning(
                            f"⚠️ 检测到发网但置信度较低: human_bbox={human_bbox}, track_id={track_id}, "
                            f"hairnet_confidence={hairnet_confidence:.3f}, "
                            f"post_process_threshold={post_process_threshold:.3f}, 标记为佩戴"
                        )
                    else:
                        # 置信度太低（<0.1），标记为未佩戴
                        has_hairnet = False
                        persons_without_hairnet += 1
                        logger.warning(
                            f"❌ 发网检测置信度太低: human_bbox={human_bbox}, track_id={track_id}, "
                            f"hairnet_confidence={hairnet_confidence:.3f}, 标记为未佩戴"
                        )
                else:
                    # 没有检测到发网，结果不明确
                    # 优化：不立即判定为未佩戴，而是标记为"不确定"
                    # 这样可以避免误判（可能发网太小或角度问题导致检测不到）
                    has_hairnet = None
                    logger.warning(
                        f"⚠️ 发网检测模型未检测到发网: human_bbox={human_bbox}, track_id={track_id}, "
                        f"human_confidence={human_confidence:.3f}, "
                        f"检测阈值={detection_conf}, ROI大小={head_roi.shape}"
                    )

                # 保存ROI（检测后，带检测结果标记）
                if self.save_debug_roi:
                    result_label = None
                    if has_hairnet is True:
                        result_label = "detected"
                    elif has_hairnet is False:
                        result_label = "not_detected"
                    else:
                        result_label = "uncertain"

                    self._save_debug_roi(
                        head_roi,
                        track_id,
                        human_bbox,
                        (roi_x1, roi_y1, roi_x2, roi_y2),
                        detection_result=result_label,
                    )

                # 创建合规性检测结果（兼容原有格式）
                compliance_detections.append(
                    {
                        "bbox": human_bbox,
                        "has_hairnet": has_hairnet,
                        "confidence": human_confidence,
                        "hairnet_confidence": hairnet_confidence,
                    }
                )

            # 更新统计信息
            self.total_detections += len(human_detections)
            self.hairnet_detections += persons_with_hairnet

            # 计算合规率
            total_persons = len(human_detections)
            compliance_rate = (
                (persons_with_hairnet / total_persons) if total_persons > 0 else 0.0
            )

            # 计算平均置信度
            if compliance_detections:
                average_confidence = sum(
                    det["confidence"] for det in compliance_detections
                ) / len(compliance_detections)
            else:
                average_confidence = 0.0

            logger.info(
                f"ROI发网检测完成: 检测了 {total_persons} 个人, "
                f"佩戴={persons_with_hairnet}, 未佩戴={persons_without_hairnet}, "
                f"合规率={compliance_rate:.2f}"
            )

            # 返回兼容格式的结果
            return {
                "total_persons": total_persons,
                "persons_with_hairnet": persons_with_hairnet,
                "persons_without_hairnet": persons_without_hairnet,
                "compliance_rate": compliance_rate,
                "detections": compliance_detections,
                "average_confidence": average_confidence,
                "error": None,
            }

        except Exception as e:
            logger.error(f"ROI发网检测失败: {e}", exc_info=True)
            return {
                "total_persons": len(human_detections),
                "persons_with_hairnet": 0,
                "persons_without_hairnet": len(human_detections),
                "compliance_rate": 0.0,
                "detections": [],
                "average_confidence": 0.0,
                "error": str(e),
            }

    def _batch_detect_hairnet_in_rois(
        self,
        image: np.ndarray,
        human_detections: List[Dict],
    ) -> Dict[str, Any]:
        """
        批量检测多个头部ROI（任务3.3：批量ROI检测优化）

        Args:
            image: 完整图像
            human_detections: 人体检测结果列表

        Returns:
            检测结果字典（兼容detect_hairnet_compliance格式）
        """
        try:
            # 步骤1：收集所有头部ROI
            head_rois = []
            roi_info = []  # 保存ROI的元信息（用于坐标映射）

            for i, human_det in enumerate(human_detections):
                human_bbox = human_det.get("bbox", [0, 0, 0, 0])
                track_id = human_det.get("track_id", i)
                human_confidence = human_det.get("confidence", 1.0)

                # 提取头部ROI（优化：使用30%的头部区域，更精确地只包含头部和发网）
                x1, y1, x2, y2 = map(int, human_bbox)
                person_height = y2 - y1
                person_width = x2 - x1

                # 优化：使用配置化的头部区域比例，只包含头部和发网
                head_height = int(person_height * self.roi_head_ratio)

                # 确保ROI有效
                if x2 <= x1 or y2 <= y1 or head_height <= 0:
                    logger.warning(f"无效的人体边界框: {human_bbox}")
                    continue

                # 优化：使用配置化的padding，确保包含发网边缘但不超出太多
                padding_height = int(head_height * self.roi_padding_height_ratio)
                padding_width = int(person_width * self.roi_padding_width_ratio)

                roi_x1 = max(0, x1 - padding_width)
                roi_y1 = max(0, y1 - padding_height)
                roi_x2 = min(image.shape[1], x2 + padding_width)
                roi_y2 = min(image.shape[0], y1 + head_height + padding_height)

                head_roi = image[roi_y1:roi_y2, roi_x1:roi_x2]

                if head_roi.size == 0:
                    logger.warning(f"头部ROI为空: {human_bbox}")
                    continue

                # 诊断日志：记录ROI提取的详细信息
                roi_width, roi_height = head_roi.shape[1], head_roi.shape[0]
                min_roi_size = self.roi_min_size  # 最小ROI尺寸阈值（可配置）
                is_small_roi = roi_width < min_roi_size or roi_height < min_roi_size

                logger.warning(
                    f"📊 ROI提取详情（批量）: track_id={track_id}, "
                    f"人体bbox=({x1}, {y1}, {x2}, {y2}), "
                    f"人体尺寸=({person_width}, {person_height}), "
                    f"头部高度={head_height} ({self.roi_head_ratio*100:.0f}% of person_height), "
                    f"ROI区域=({roi_x1}, {roi_y1}, {roi_x2}, {roi_y2}), "
                    f"ROI尺寸={head_roi.shape} ({roi_width}x{roi_height}), "
                    f"padding=({padding_width}, {padding_height}), "
                    f"是否小ROI={is_small_roi} (最小阈值={min_roi_size}), "
                    f"配置参数: head_ratio={self.roi_head_ratio}, "
                    f"padding_h={self.roi_padding_height_ratio}, padding_w={self.roi_padding_width_ratio}"
                )

                # 保存ROI用于调试（如果启用）
                if self.save_debug_roi:
                    self._save_debug_roi(
                        head_roi,
                        track_id,
                        human_bbox,
                        (roi_x1, roi_y1, roi_x2, roi_y2),
                        detection_result="before_detection",
                    )

                # 注意：预处理（CLAHE + 锐化）会改变图像特征，导致模型无法识别
                # 测试发现：不使用预处理可以正常检测到发网，使用预处理后检测失败
                # 因此暂时禁用预处理，直接使用原始ROI
                # 如果后续需要预处理，可以添加开关控制或降低预处理强度
                # try:
                #     lab = cv2.cvtColor(head_roi, cv2.COLOR_BGR2LAB)
                #     l, a, b = cv2.split(lab)
                #     clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                #     l_enhanced = clahe.apply(l)
                #     lab_enhanced = cv2.merge([l_enhanced, a, b])
                #     head_roi = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
                #     kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]]) * 0.1
                #     head_roi = cv2.filter2D(head_roi, -1, kernel)
                # except Exception as e:
                #     logger.debug(f"ROI预处理失败，使用原始ROI: {e}")

                head_rois.append(head_roi)
                roi_info.append(
                    {
                        "index": i,
                        "human_bbox": human_bbox,
                        "track_id": track_id,
                        "human_confidence": human_confidence,
                        "roi_offset": (roi_x1, roi_y1),  # ROI在原图中的偏移
                        "roi_size": (roi_x2 - roi_x1, roi_y2 - roi_y1),
                    }
                )

            if not head_rois:
                return {
                    "total_persons": len(human_detections),
                    "persons_with_hairnet": 0,
                    "persons_without_hairnet": len(human_detections),
                    "compliance_rate": 0.0,
                    "detections": [],
                    "average_confidence": 0.0,
                    "error": None,
                }

            # 步骤2：批量推理（YOLO支持批量输入）
            # 优化：使用配置化的检测阈值，以提高检测敏感度
            detection_conf = self.roi_detection_confidence
            iou = self.iou_thres

            logger.info(
                f"批量发网检测: 人数={len(human_detections)}, "
                f"ROI数量={len(head_rois)}, "
                f"检测阈值={detection_conf}, "
                f"配置阈值={self.conf_thres}"
            )

            try:
                # YOLO模型支持批量输入（列表形式）
                # 使用低阈值进行检测，捕获更多可能的发网
                # 重要：指定imgsz=640与训练时保持一致，确保检测准确率
                logger.warning(
                    f"🔍 开始批量ROI模型推理: "
                    f"ROI数量={len(head_rois)}, "
                    f"检测阈值={detection_conf}, "
                    f"模型输入尺寸=640x640 (自动resize)"
                )
                batch_results = self.model(
                    head_rois, conf=detection_conf, iou=iou, imgsz=640, verbose=False
                )

                # 详细诊断：输出模型原始结果
                total_boxes = 0
                all_raw_detections = []
                for roi_idx, r in enumerate(batch_results):
                    boxes = r.boxes
                    if boxes is not None:
                        total_boxes += len(boxes)
                        for box in boxes:
                            conf = float(box.conf[0])
                            cls = int(box.cls[0])
                            cls_name = self.model.names[cls]
                            all_raw_detections.append(
                                {
                                    "roi_idx": roi_idx,
                                    "class": cls_name,
                                    "confidence": conf,
                                    "bbox": box.xyxy[0].cpu().numpy().tolist(),
                                }
                            )

                logger.warning(
                    f"✅ 批量ROI模型推理完成: "
                    f"结果数量={len(batch_results)}, "
                    f"检测框总数={total_boxes}, "
                    f"ROI数量={len(head_rois)}, "
                    f"检测阈值={detection_conf}, "
                    f"原始检测结果={all_raw_detections}"
                )
            except Exception as e:
                logger.error(f"批量ROI发网检测失败: {e}", exc_info=True)
                # 回退到逐个检测
                return self._detect_hairnet_in_rois(
                    image, human_detections, use_batch=False
                )

            # 步骤3：处理批量结果并映射坐标
            compliance_detections = []
            persons_with_hairnet = 0
            persons_without_hairnet = 0
            all_detections = []

            for roi_idx, (result, info) in enumerate(zip(batch_results, roi_info)):
                roi_x1, roi_y1 = info["roi_offset"]
                track_id = info.get("track_id", roi_idx)
                human_bbox = info.get("human_bbox", [0, 0, 0, 0])
                human_confidence = info.get("human_confidence", 1.0)

                # 处理该ROI的检测结果
                has_hairnet = None
                hairnet_confidence = 0.0
                roi_detections = []

                boxes = result.boxes
                num_boxes = len(boxes) if boxes is not None else 0
                all_classes_found = []  # 记录所有检测到的类别
                logger.info(
                    f"批量检测ROI {roi_idx}: track_id={track_id}, "
                    f"检测到 {num_boxes} 个目标, "
                    f"human_bbox={human_bbox}"
                )

                if boxes is None or num_boxes == 0:
                    logger.warning(
                        f"⚠️ 批量检测ROI {roi_idx}: 未检测到任何目标, "
                        f"track_id={track_id}, "
                        f"检测阈值={detection_conf}, "
                        f"human_bbox={human_bbox}"
                    )
                    # 标记为"不确定"，稍后会尝试扩展ROI检测
                    has_hairnet = None
                    hairnet_confidence = 0.0
                else:
                    for box in boxes:
                        # ROI内的坐标
                        roi_x1_det, roi_y1_det, roi_x2_det, roi_y2_det = (
                            box.xyxy[0].cpu().numpy()
                        )
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        cls_name = self.model.names[cls]
                        all_classes_found.append((cls_name, conf))

                        logger.debug(
                            f"批量检测ROI {roi_idx}: class={cls_name}, confidence={conf:.3f}, "
                            f"bbox=[{roi_x1_det:.1f}, {roi_y1_det:.1f}, {roi_x2_det:.1f}, {roi_y2_det:.1f}]"
                        )

                        # 映射回原图坐标
                        orig_x1 = float(roi_x1 + roi_x1_det)
                        orig_y1 = float(roi_y1 + roi_y1_det)
                        orig_x2 = float(roi_x1 + roi_x2_det)
                        orig_y2 = float(roi_y1 + roi_y2_det)

                        detection = {
                            "class": str(cls_name),
                            "confidence": float(conf),
                            "bbox": [orig_x1, orig_y1, orig_x2, orig_y2],
                        }
                        roi_detections.append(detection)
                        all_detections.append(detection)

                        # 检查是否为发网类别
                        if cls_name.lower() == "hairnet":
                            if has_hairnet is None:
                                has_hairnet = True
                                hairnet_confidence = conf
                                logger.info(
                                    f"✅ 批量检测：检测到发网: ROI={roi_idx}, track_id={track_id}, "
                                    f"confidence={conf:.3f}"
                                )
                            elif conf > hairnet_confidence:
                                hairnet_confidence = conf
                                logger.info(
                                    f"✅ 批量检测：更新发网置信度: ROI={roi_idx}, track_id={track_id}, "
                                    f"confidence={conf:.3f}"
                                )

                    # 记录所有检测到的类别（用于调试）
                    if all_classes_found:
                        logger.info(
                            f"批量检测ROI {roi_idx}: track_id={track_id}, "
                            f"检测到的所有类别={all_classes_found}, "
                            f"发网置信度={hairnet_confidence:.3f}"
                        )
                    else:
                        logger.warning(
                            f"⚠️ 批量检测ROI {roi_idx}: 未检测到任何类别, "
                            f"track_id={track_id}, "
                            f"检测阈值={detection_conf}, "
                            f"human_bbox={human_bbox}"
                        )

                # 备用策略：如果未检测到发网（has_hairnet为None或False），尝试扩展ROI检测
                logger.warning(
                    f"检查扩展ROI检测条件（批量）: track_id={track_id}, "
                    f"has_hairnet={has_hairnet}, "
                    f"type={type(has_hairnet)}, "
                    f"is None={has_hairnet is None}, "
                    f"is False={has_hairnet is False}"
                )
                if has_hairnet is None or has_hairnet is False:
                    logger.warning(
                        f"✅ 触发扩展ROI检测（批量）: track_id={track_id}, "
                        f"has_hairnet={has_hairnet}"
                    )
                    roi_x1, roi_y1 = info["roi_offset"]
                    roi_size = info["roi_size"]
                    roi_x2 = roi_x1 + roi_size[0]
                    roi_y2 = roi_y1 + roi_size[1]

                    for attempt in range(self.roi_expansion_attempts):
                        expansion = self.roi_expansion_pixels * (attempt + 1)
                        expanded_roi_x1 = max(0, roi_x1 - expansion)
                        expanded_roi_y1 = max(0, roi_y1 - expansion)
                        expanded_roi_x2 = min(image.shape[1], roi_x2 + expansion)
                        expanded_roi_y2 = min(image.shape[0], roi_y2 + expansion)
                        expanded_roi = image[
                            expanded_roi_y1:expanded_roi_y2,
                            expanded_roi_x1:expanded_roi_x2,
                        ]

                        logger.warning(
                            f"扩展ROI提取（批量）: track_id={track_id}, "
                            f"尝试={attempt + 1}/{self.roi_expansion_attempts}, "
                            f"原始ROI=({roi_x1}, {roi_y1}, {roi_x2}, {roi_y2}), "
                            f"扩展ROI=({expanded_roi_x1}, {expanded_roi_y1}, {expanded_roi_x2}, {expanded_roi_y2}), "
                            f"扩展ROI大小={expanded_roi.shape if expanded_roi.size > 0 else '空'}"
                        )

                        if expanded_roi.size == 0:
                            continue

                        logger.warning(
                            f"🔍 尝试扩展ROI检测（批量）: track_id={track_id}, "
                            f"扩展ROI大小={expanded_roi.shape}, "
                            f"原因={'未检测到任何目标' if not all_classes_found else '未检测到发网'}"
                        )
                        try:
                            expanded_conf = max(
                                self.roi_min_positive_confidence,
                                detection_conf * self.roi_expansion_conf_scale,
                            )
                            logger.warning(
                                f"开始扩展ROI模型推理（批量）: track_id={track_id}, "
                                f"尝试={attempt + 1}/{self.roi_expansion_attempts}, "
                                f"扩展ROI大小={expanded_roi.shape}, "
                                f"扩展像素={expansion}, "
                                f"检测阈值={expanded_conf}, "
                                f"模型输入尺寸=640x640 (自动resize)"
                            )

                            # 保存扩展ROI用于调试
                            if self.save_debug_roi:
                                self._save_debug_roi(
                                    expanded_roi,
                                    track_id,
                                    human_bbox,
                                    (
                                        expanded_roi_x1,
                                        expanded_roi_y1,
                                        expanded_roi_x2,
                                        expanded_roi_y2,
                                    ),
                                    detection_result=f"expanded_attempt_{attempt + 1}",
                                )

                            expanded_results = self.model(
                                expanded_roi,
                                conf=expanded_conf,
                                iou=iou,
                                imgsz=640,
                                verbose=False,
                            )

                            logger.warning(
                                f"扩展ROI模型推理完成（批量）: track_id={track_id}, "
                                f"尝试={attempt + 1}/{self.roi_expansion_attempts}, "
                                f"结果数量={len(expanded_results)}"
                            )

                            expanded_detections = []
                            for r_idx, r in enumerate(expanded_results):
                                boxes_expanded = r.boxes
                                num_boxes = (
                                    len(boxes_expanded)
                                    if boxes_expanded is not None
                                    else 0
                                )
                                logger.warning(
                                    f"扩展ROI结果 {r_idx}（批量）: track_id={track_id}, "
                                    f"检测框数量={num_boxes}"
                                )
                                if boxes_expanded is not None:
                                    for box_idx, box in enumerate(boxes_expanded):
                                        cls = int(box.cls[0])
                                        cls_name = self.model.names[cls]
                                        conf = float(box.conf[0])
                                        expanded_detections.append((cls_name, conf))

                                        if cls_name.lower() == "hairnet":
                                            box_x1, box_y1, box_x2, box_y2 = (
                                                box.xyxy[0].cpu().numpy()
                                            )
                                            box_center_x = (
                                                box_x1 + box_x2
                                            ) / 2 + expanded_roi_x1
                                            box_center_y = (
                                                box_y1 + box_y2
                                            ) / 2 + expanded_roi_y1

                                            logger.warning(
                                                f"扩展ROI检测到hairnet类别: track_id={track_id}, "
                                                f"confidence={conf:.3f}, "
                                                f"位置=({box_center_x:.0f}, {box_center_y:.0f}), "
                                                f"原始ROI=({roi_x1}, {roi_y1}, {roi_x2}, {roi_y2})"
                                            )

                                            if (
                                                roi_x1 - expansion
                                                <= box_center_x
                                                <= roi_x2 + expansion
                                                and roi_y1 - expansion
                                                <= box_center_y
                                                <= roi_y2 + expansion
                                            ):
                                                has_hairnet = True
                                                hairnet_confidence = max(
                                                    hairnet_confidence, conf
                                                )
                                                logger.warning(
                                                    f"✅ 扩展ROI检测到发网（批量）: track_id={track_id}, "
                                                    f"confidence={conf:.3f}, "
                                                    f"位置在原始ROI附近"
                                                )
                                            else:
                                                logger.warning(
                                                    f"⚠️ 扩展ROI检测到发网但位置不在原始ROI附近: "
                                                    f"track_id={track_id}, confidence={conf:.3f}, "
                                                    f"位置=({box_center_x:.0f}, {box_center_y:.0f}), "
                                                    f"原始ROI范围=({roi_x1-expansion}, {roi_y1-expansion}) "
                                                    f"-> ({roi_x2+expansion}, {roi_y2+expansion})"
                                                )

                            if expanded_detections:
                                logger.warning(
                                    f"扩展ROI检测结果（批量）: track_id={track_id}, "
                                    f"检测到的类别={expanded_detections}"
                                )
                            else:
                                logger.warning(
                                    f"扩展ROI检测未检测到任何目标（批量）: track_id={track_id}, "
                                    f"扩展ROI大小={expanded_roi.shape}, "
                                    f"检测阈值={expanded_conf}"
                                )

                            if has_hairnet:
                                break
                        except Exception as e:
                            logger.warning(
                                f"扩展ROI检测失败（批量）: track_id={track_id}, 尝试={attempt + 1}, error={e}",
                                exc_info=True,
                            )

                    if has_hairnet is None:
                        has_hairnet = None
                        hairnet_confidence = 0.0

                # 优化：改进发网佩戴状态判断逻辑（与逐个检测保持一致）

                if has_hairnet is True:
                    # 检测到发网，使用更宽松的阈值进行最终判断
                    # 进一步降低后处理阈值要求，提高检测敏感度
                    post_process_threshold = min(
                        self.conf_thres, self.roi_postprocess_threshold_cap
                    )

                    if hairnet_confidence >= post_process_threshold:
                        persons_with_hairnet += 1
                        logger.info(
                            f"✅ 批量检测：确认佩戴发网: track_id={track_id}, "
                            f"hairnet_confidence={hairnet_confidence:.3f}, "
                            f"post_process_threshold={post_process_threshold:.3f}"
                        )
                    elif hairnet_confidence >= self.roi_min_positive_confidence:
                        persons_with_hairnet += 1
                        logger.warning(
                            f"⚠️ 批量检测：发网置信度较低，但仍标记为佩戴: track_id={track_id}, "
                            f"hairnet_confidence={hairnet_confidence:.3f}, "
                            f"post_process_threshold={post_process_threshold:.3f}"
                        )
                else:
                    # 没有检测到发网，结果不明确
                    has_hairnet = None
                    logger.warning(
                        f"⚠️ 批量检测：发网检测模型未检测到发网: track_id={track_id}, "
                        f"human_confidence={human_confidence:.3f}, "
                        f"检测阈值={detection_conf}, "
                        f"检测到的类别={all_classes_found}"
                    )

                # 保存ROI（检测后，带检测结果标记）
                if self.save_debug_roi:
                    # 获取对应的ROI图像
                    roi_idx = info.get("index", roi_idx)
                    if roi_idx < len(head_rois):
                        roi_image = head_rois[roi_idx]
                        roi_offset = info.get("roi_offset", (0, 0))
                        roi_size = info.get("roi_size", (0, 0))
                        roi_coords = (
                            roi_offset[0],
                            roi_offset[1],
                            roi_offset[0] + roi_size[0],
                            roi_offset[1] + roi_size[1],
                        )

                        result_label = None
                        if has_hairnet is True:
                            result_label = "detected"
                        elif has_hairnet is False:
                            result_label = "not_detected"
                        else:
                            result_label = "uncertain"

                        self._save_debug_roi(
                            roi_image,
                            track_id,
                            info["human_bbox"],
                            roi_coords,
                            detection_result=result_label,
                        )

                # 创建合规性检测结果
                compliance_detections.append(
                    {
                        "bbox": info["human_bbox"],
                        "has_hairnet": has_hairnet,
                        "confidence": info["human_confidence"],
                        "hairnet_confidence": hairnet_confidence,
                    }
                )

            # 更新统计信息
            self.total_detections += len(human_detections)
            self.hairnet_detections += persons_with_hairnet

            # 计算合规率
            total_persons = len(human_detections)
            compliance_rate = (
                (persons_with_hairnet / total_persons) if total_persons > 0 else 0.0
            )

            # 计算平均置信度
            if compliance_detections:
                average_confidence = sum(
                    det["confidence"] for det in compliance_detections
                ) / len(compliance_detections)
            else:
                average_confidence = 0.0

            logger.info(
                f"批量ROI发网检测完成: 检测了 {total_persons} 个人, "
                f"佩戴={persons_with_hairnet}, 未佩戴={persons_without_hairnet}, "
                f"合规率={compliance_rate:.2f}"
            )

            return {
                "total_persons": total_persons,
                "persons_with_hairnet": persons_with_hairnet,
                "persons_without_hairnet": persons_without_hairnet,
                "compliance_rate": compliance_rate,
                "detections": compliance_detections,
                "average_confidence": average_confidence,
                "error": None,
            }

        except Exception as e:
            logger.error(f"批量ROI发网检测失败: {e}", exc_info=True)
            # 回退到逐个检测
            logger.info("回退到逐个ROI检测")
            return self._detect_hairnet_in_rois(
                image, human_detections, use_batch=False
            )

    def _boxes_overlap(self, box1: List[float], box2: List[float]) -> bool:
        """
        检查两个边界框是否重叠

        Args:
            box1: 第一个边界框 [x1, y1, x2, y2]
            box2: 第二个边界框 [x1, y1, x2, y2]

        Returns:
            bool: 是否重叠
        """
        try:
            x1_1, y1_1, x2_1, y2_1 = box1
            x1_2, y1_2, x2_2, y2_2 = box2

            # 检查是否有重叠
            return not (x2_1 < x1_2 or x2_2 < x1_1 or y2_1 < y1_2 or y2_2 < y1_1)
        except Exception:
            return False
