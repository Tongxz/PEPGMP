#!/usr/bin/env python

"""
YOLOv8 发网检测器实现

基于 YOLOv8 的发网检测器，可以直接检测图像中的发网，无需先检测人体再提取头部区域
"""

import logging
import os
import sys
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

logger = logging.getLogger(__name__)


class YOLOHairnetDetector:
    """
    基于 YOLOv8 的发网检测器

    直接使用 YOLOv8 模型检测图像中的发网，无需先检测人体再提取头部区域
    """

    def __init__(
        self,
        model_path: str = "models/hairnet_detection/hairnet_detection.pt",
        device: str = "auto",
        conf_thres: float = 0.25,
        iou_thres: float = 0.45,
    ):
        """
        初始化 YOLOv8 发网检测器

        Args:
            model_path: YOLOv8 模型路径，默认为 'models/hairnet_detection/models/hairnet_detection/hairnet_detection.pt'
            device: 计算设备，可选 'cpu', 'cuda', 'auto'
            conf_thres: 置信度阈值，默认为 0.25
            iou_thres: IoU 阈值，默认为 0.45
        """
        project_root = Path(__file__).resolve().parents[2]
        if not Path(model_path).is_absolute():
            self.model_path = str(project_root / model_path)
        else:
            self.model_path = model_path

        self.device = self._get_device(device)
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        self.model = self._load_model()

        # 统计信息
        self.total_detections = 0
        self.hairnet_detections = 0

        logger.info(f"YOLOHairnetDetector 初始化成功，使用设备: {self.device}")

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
            results = self.model(image, conf=conf, iou=iou, verbose=False)

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
                logger.info(f"使用提供的人体检测结果: 检测到 {len(human_detections)} 个人")

            # 确保图像是numpy数组格式
            if isinstance(image, str):
                image_array = cv2.imread(image)
                if image_array is None:
                    raise ValueError(f"无法读取图像文件: {image}")
            else:
                image_array = image

            # 优化：如果提供了人体检测结果，使用ROI检测（任务3.1）
            if human_detections and len(human_detections) > 0:
                # 使用ROI检测（只检测头部区域）
                result = self._detect_hairnet_in_rois(image_array, human_detections)
            else:
                # 回退到全帧检测
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
                            if hairnet_detections:
                                hairnet_confidence = max(
                                    det.get("confidence", 0.0)
                                    for det in hairnet_detections
                                    if det.get("class", "").lower() == "hairnet"
                                )
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
                
                # 提取头部ROI（人体高度的30%）
                x1, y1, x2, y2 = map(int, human_bbox)
                person_height = y2 - y1
                head_height = int(person_height * 0.3)  # 头部占人体高度的30%
                
                # 确保ROI有效
                if x2 <= x1 or y2 <= y1 or head_height <= 0:
                    logger.warning(f"无效的人体边界框: {human_bbox}")
                    continue
                
                # 裁剪头部ROI（添加一些padding）
                padding = int(head_height * 0.1)  # 10%的padding
                roi_x1 = max(0, x1 - padding)
                roi_y1 = max(0, y1 - padding)
                roi_x2 = min(image.shape[1], x2 + padding)
                roi_y2 = min(image.shape[0], y1 + head_height + padding)
                
                head_roi = image[roi_y1:roi_y2, roi_x1:roi_x2]
                
                if head_roi.size == 0:
                    logger.warning(f"头部ROI为空: {human_bbox}")
                    continue
                
                # 在ROI上运行发网检测
                conf = self.conf_thres
                iou = self.iou_thres
                
                try:
                    results = self.model(head_roi, conf=conf, iou=iou, verbose=False)
                except Exception as e:
                    logger.error(f"ROI发网检测失败: {e}")
                    continue
                
                # 处理检测结果
                has_hairnet = None  # None表示检测结果不明确
                hairnet_confidence = 0.0
                roi_detections = []
                
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        # ROI内的坐标
                        roi_x1_det, roi_y1_det, roi_x2_det, roi_y2_det = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        cls_name = self.model.names[cls]
                        
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
                            elif conf > hairnet_confidence:
                                hairnet_confidence = conf
                
                # 判断发网佩戴状态
                if has_hairnet is None:
                    # 没有检测到发网，结果不明确
                    has_hairnet = None
                    logger.debug(
                        f"发网检测模型未检测到发网，检测结果不明确: "
                        f"human_bbox={human_bbox}, confidence={human_confidence}"
                    )
                elif has_hairnet is True:
                    persons_with_hairnet += 1
                else:
                    persons_without_hairnet += 1
                
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
                
                # 提取头部ROI（人体高度的30%）
                x1, y1, x2, y2 = map(int, human_bbox)
                person_height = y2 - y1
                head_height = int(person_height * 0.3)
                
                # 确保ROI有效
                if x2 <= x1 or y2 <= y1 or head_height <= 0:
                    logger.warning(f"无效的人体边界框: {human_bbox}")
                    continue
                
                # 裁剪头部ROI（添加padding）
                padding = int(head_height * 0.1)
                roi_x1 = max(0, x1 - padding)
                roi_y1 = max(0, y1 - padding)
                roi_x2 = min(image.shape[1], x2 + padding)
                roi_y2 = min(image.shape[0], y1 + head_height + padding)
                
                head_roi = image[roi_y1:roi_y2, roi_x1:roi_x2]
                
                if head_roi.size == 0:
                    logger.warning(f"头部ROI为空: {human_bbox}")
                    continue
                
                head_rois.append(head_roi)
                roi_info.append({
                    "index": i,
                    "human_bbox": human_bbox,
                    "track_id": track_id,
                    "human_confidence": human_confidence,
                    "roi_offset": (roi_x1, roi_y1),  # ROI在原图中的偏移
                    "roi_size": (roi_x2 - roi_x1, roi_y2 - roi_y1),
                })
            
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
            conf = self.conf_thres
            iou = self.iou_thres
            
            try:
                # YOLO模型支持批量输入（列表形式）
                batch_results = self.model(head_rois, conf=conf, iou=iou, verbose=False)
            except Exception as e:
                logger.error(f"批量ROI发网检测失败: {e}")
                # 回退到逐个检测
                return self._detect_hairnet_in_rois(image, human_detections, use_batch=False)
            
            # 步骤3：处理批量结果并映射坐标
            compliance_detections = []
            persons_with_hairnet = 0
            persons_without_hairnet = 0
            all_detections = []
            
            for roi_idx, (result, info) in enumerate(zip(batch_results, roi_info)):
                roi_x1, roi_y1 = info["roi_offset"]
                
                # 处理该ROI的检测结果
                has_hairnet = None
                hairnet_confidence = 0.0
                roi_detections = []
                
                boxes = result.boxes
                for box in boxes:
                    # ROI内的坐标
                    roi_x1_det, roi_y1_det, roi_x2_det, roi_y2_det = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    cls_name = self.model.names[cls]
                    
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
                        elif conf > hairnet_confidence:
                            hairnet_confidence = conf
                
                # 判断发网佩戴状态
                if has_hairnet is None:
                    has_hairnet = None
                    logger.debug(
                        f"发网检测模型未检测到发网，检测结果不明确: "
                        f"human_bbox={info['human_bbox']}, confidence={info['human_confidence']}"
                    )
                elif has_hairnet is True:
                    persons_with_hairnet += 1
                else:
                    persons_without_hairnet += 1
                
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
            return self._detect_hairnet_in_rois(image, human_detections, use_batch=False)

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
