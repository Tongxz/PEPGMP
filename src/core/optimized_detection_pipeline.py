#!/usr/bin/env python3
"""
优化的检测管道 - 实现模型复用、缓存和统一处理

主要优化点：
1. 模型加载移至初始化阶段，避免重复加载
2. 构建统一的BehaviorDetectionPipeline，复用中间结果
3. 明确检测顺序和依赖关系
4. 增加缓存机制，特别是视频流处理
"""

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.config.unified_params import get_unified_params
from src.core.behavior import DeepBehaviorRecognizer
from src.detection.detector import HumanDetector
from src.detection.hairnet_detector import HairnetDetector
from src.detection.motion_analyzer import MotionAnalyzer
from src.detection.pose_detector import PoseDetectorFactory
from src.utils.logger import get_logger

# 级联相关依赖（可选）
try:
    from ultralytics import YOLO as _YOLOHeavy
except Exception:  # 发生错误时延迟到运行期再判断
    _YOLOHeavy = None  # type: ignore

try:
    from src.config.model_config import ModelConfig as _MC
except Exception:
    _MC = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """统一的检测结果数据结构"""

    person_detections: List[Dict]
    hairnet_results: List[Dict]
    handwash_results: List[Dict]
    sanitize_results: List[Dict]
    processing_times: Dict[str, float]
    annotated_image: Optional[np.ndarray] = None
    frame_cache_key: Optional[str] = None


@dataclass
class CachedDetection:
    """缓存的检测结果"""

    result: DetectionResult
    timestamp: float
    frame_hash: str


class FrameCache:
    """帧缓存管理器 - 用于视频流处理优化"""

    def __init__(self, max_size: int = 100, ttl: float = 30.0):
        self.max_size = max_size
        self.ttl = ttl  # 缓存生存时间（秒）
        self.cache: OrderedDict[str, CachedDetection] = OrderedDict()
        self.lock = Lock()

    def _generate_frame_hash(self, frame: np.ndarray) -> str:
        """生成帧的哈希值用于缓存键"""
        # 使用帧的形状和部分像素值生成简单哈希
        h, w = frame.shape[:2]
        sample_pixels = frame[:: h // 10, :: w // 10].flatten()[:100]
        return f"{h}x{w}_{hash(sample_pixels.tobytes())}"

    def get(self, frame: np.ndarray) -> Optional[DetectionResult]:
        """从缓存获取检测结果"""
        frame_hash = self._generate_frame_hash(frame)

        with self.lock:
            if frame_hash in self.cache:
                cached = self.cache[frame_hash]
                # 检查是否过期
                if time.time() - cached.timestamp <= self.ttl:
                    # 移到最后（LRU）
                    self.cache.move_to_end(frame_hash)
                    logger.debug(f"缓存命中: {frame_hash}")
                    return cached.result
                else:
                    # 过期，删除
                    del self.cache[frame_hash]

        return None

    def put(self, frame: np.ndarray, result: DetectionResult):
        """将检测结果放入缓存"""
        frame_hash = self._generate_frame_hash(frame)

        with self.lock:
            # 如果缓存已满，删除最旧的
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)

            cached = CachedDetection(
                result=result, timestamp=time.time(), frame_hash=frame_hash
            )
            self.cache[frame_hash] = cached
            logger.debug(f"缓存存储: {frame_hash}")

    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            logger.info("缓存已清空")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            return {
                "cache_size": len(self.cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
            }


class OptimizedDetectionPipeline:
    """优化的检测管道 - 统一处理所有检测任务"""

    def __init__(
        self,
        human_detector=None,
        hairnet_detector=None,
        behavior_recognizer=None,
        pose_detector=None,  # 新增参数
        enable_cache: bool = True,
        cache_size: int = 100,
        cache_ttl: float = 30.0,
        cascade_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化优化检测管道

        Args:
            human_detector: 人体检测器
            hairnet_detector: 发网检测器
            behavior_recognizer: 行为识别器
            pose_detector: 姿态检测器实例 (可选，如果提供则使用此实例)
            enable_cache: 是否启用缓存
            cache_size: 缓存大小
            cache_ttl: 缓存生存时间
        """
        self.human_detector = human_detector
        self.hairnet_detector = hairnet_detector
        self.behavior_recognizer = behavior_recognizer

        # 初始化姿态检测器
        if pose_detector is not None:
            self.pose_detector = pose_detector
            logger.info(f"姿态检测器 (外部提供) 初始化成功")
        else:
            try:
                params = get_unified_params()
                pose_backend = params.pose_detection.backend
                pose_params = params.pose_detection

                self.pose_detector = PoseDetectorFactory.create(
                    backend=pose_backend,
                    model_path=pose_params.model_path,
                    device=pose_params.device,
                )
                logger.info(f"姿态检测器 ({pose_backend}) 初始化成功")
            except Exception as e:
                logger.warning(f"姿态检测器初始化失败: {e}")
                self.pose_detector = None

        # 初始化缓存
        self.enable_cache = enable_cache
        if enable_cache:
            self.frame_cache = FrameCache(max_size=cache_size, ttl=cache_ttl)
        else:
            self.frame_cache = None

        # 性能统计
        self.stats = {
            "total_detections": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_processing_time": 0.0,
        }

        logger.info(f"优化检测管道初始化完成，缓存: {'启用' if enable_cache else '禁用'}")

        # 级联相关
        self.cascade: Dict[str, Any] = cascade_config or {}
        self._cascade_model = None  # 惰性加载重模型
        self.cascade_stats = {
            "triggers": 0,
            "refined": 0,
            "time_total": 0.0,
        }

    def detect(self, image: np.ndarray, **kwargs) -> DetectionResult:
        """检测方法 - detect_comprehensive的别名，保持接口兼容性"""
        return self.detect_comprehensive(
            image,
            enable_hairnet=kwargs.get("enable_hairnet", True),
            enable_handwash=kwargs.get("enable_handwash", True),
            enable_sanitize=kwargs.get("enable_sanitize", True),
        )

    def detect_comprehensive(
        self,
        image: np.ndarray,
        enable_hairnet: bool = True,
        enable_handwash: bool = True,
        enable_sanitize: bool = True,
        force_refresh: bool = False,
    ) -> DetectionResult:
        """
        综合检测 - 统一入口点

        Args:
            image: 输入图像
            enable_hairnet: 是否启用发网检测
            enable_handwash: 是否启用洗手检测
            enable_sanitize: 是否启用消毒检测
            force_refresh: 是否强制刷新（忽略缓存）

        Returns:
            DetectionResult: 综合检测结果
        """
        start_time = time.time()

        # 检查缓存
        if self.enable_cache and self.frame_cache is not None and not force_refresh:
            cached_result = self.frame_cache.get(image)
            if cached_result is not None:
                self.stats["cache_hits"] += 1
                logger.debug("使用缓存的检测结果")
                return cached_result
            else:
                self.stats["cache_misses"] += 1

        # 执行检测流水线
        result = self._execute_detection_pipeline(
            image, enable_hairnet, enable_handwash, enable_sanitize
        )

        # 更新统计信息
        total_time = time.time() - start_time
        self.stats["total_detections"] += 1
        self.stats["avg_processing_time"] = (
            self.stats["avg_processing_time"] * (self.stats["total_detections"] - 1)
            + total_time
        ) / self.stats["total_detections"]

        # 存入缓存
        if self.enable_cache and self.frame_cache is not None:
            self.frame_cache.put(image, result)

        return result

    def _execute_detection_pipeline(
        self,
        image: np.ndarray,
        enable_hairnet: bool,
        enable_handwash: bool,
        enable_sanitize: bool,
    ) -> DetectionResult:
        """
        执行检测流水线 - 按优化的顺序执行各项检测

        检测顺序优化：
        1. 人体检测（基础，其他检测依赖此结果）
        2. 发网检测（依赖人体检测的头部区域）
        3. 行为检测（洗手、消毒，依赖人体检测结果）
        """
        processing_times = {}

        # 阶段1: 人体检测（必须，其他检测的基础）
        person_start = time.time()
        person_detections = self._detect_persons(image)
        processing_times["person_detection"] = time.time() - person_start

        logger.info(f"人体检测完成: 检测到 {len(person_detections)} 个人")

        # 可选：级联二次检测，对边界分数段或ROI内的目标进行重检
        try:
            t0 = time.time()
            person_detections = self._cascade_refine_persons(image, person_detections)
            processing_times["cascade_refine"] = time.time() - t0
        except Exception as e:
            processing_times["cascade_refine"] = 0.0
            logger.debug(f"级联细化跳过: {e}")

        # 阶段2: 发网检测（基于人体检测结果）
        hairnet_results = []
        if enable_hairnet and len(person_detections) > 0:
            hairnet_start = time.time()
            hairnet_results = self._detect_hairnet_for_persons(image, person_detections)
            processing_times["hairnet_detection"] = time.time() - hairnet_start
            logger.info(f"发网检测完成: 处理了 {len(hairnet_results)} 个人")
        else:
            processing_times["hairnet_detection"] = 0.0

        # 阶段3: 行为检测（基于人体检测结果）
        handwash_results = []
        sanitize_results = []

        if (enable_handwash or enable_sanitize) and len(person_detections) > 0:
            behavior_start = time.time()

            if enable_handwash:
                handwash_results = self._detect_handwash_for_persons(
                    image, person_detections
                )

            if enable_sanitize:
                sanitize_results = self._detect_sanitize_for_persons(
                    image, person_detections
                )

            processing_times["behavior_detection"] = time.time() - behavior_start
            logger.info(
                f"行为检测完成: 洗手={len(handwash_results)}, 消毒={len(sanitize_results)}"
            )
        else:
            processing_times["behavior_detection"] = 0.0

        # 阶段4: 结果可视化（可选）
        viz_start = time.time()
        annotated_image = self._create_annotated_image(
            image,
            person_detections,
            hairnet_results,
            handwash_results,
            sanitize_results,
        )
        processing_times["visualization"] = time.time() - viz_start

        # 计算总处理时间
        processing_times["total"] = sum(processing_times.values())

        return DetectionResult(
            person_detections=person_detections,
            hairnet_results=hairnet_results,
            handwash_results=handwash_results,
            sanitize_results=sanitize_results,
            processing_times=processing_times,
            annotated_image=annotated_image,
        )

    # ----------------------- 级联逻辑 -----------------------
    def _cascade_refine_persons(self, image: np.ndarray, person_detections: List[Dict]) -> List[Dict]:
        """按配置对指定目标进行级联重检并细化框/分数。

        策略：
        - 若 cascade.enable=False 或缺少 heavy_weights，则直接返回原结果；
        - 若配置了 trigger_confidence_range=[lo,hi]，仅对落入区间的目标触发；
        - 若配置了 trigger_roi（多边形），仅对中心点落入 ROI 的目标触发；
        - 在ROI（人框或指定ROI）内使用重模型检测 person 类，取最高分，映射回全图更新 bbox/score；
        - 记录触发次数、成功细化次数与耗时。
        """

        cfg = self.cascade or {}
        if not bool(cfg.get("enable", False)):
            return person_detections

        heavy_weights: Optional[str] = cfg.get("heavy_weights")
        if not heavy_weights:
            logger.warning("级联启用但未提供 heavy_weights，跳过级联")
            return person_detections

        # 惰性加载重模型
        if self._cascade_model is None:
            if _YOLOHeavy is None:
                logger.warning("未安装 ultralytics，无法执行级联重检")
                return person_detections
            try:
                self._cascade_model = _YOLOHeavy(heavy_weights)
                # 设备选择（尽量与统一策略一致）
                if _MC is not None:
                    dev = _MC().select_device(requested=None)
                    if hasattr(self._cascade_model, "to"):
                        self._cascade_model.to(dev)
                logger.info(f"级联重模型已加载: {heavy_weights}")
            except Exception as e:
                logger.warning(f"级联重模型加载失败，跳过级联: {e}")
                return person_detections

        trig_range = cfg.get("trigger_confidence_range") or None
        roi_poly = cfg.get("trigger_roi") or None  # [[x,y], ...]

        def _in_range(score: float) -> bool:
            try:
                if not trig_range or len(trig_range) != 2:
                    return True
                lo, hi = float(trig_range[0]), float(trig_range[1])
                return (lo <= float(score) <= hi)
            except Exception:
                return True

        def _pt_in_poly(px: float, py: float, poly: List[List[float]]) -> bool:
            # 射线法
            inside = False
            n = len(poly)
            for i in range(n):
                x1, y1 = poly[i]
                x2, y2 = poly[(i + 1) % n]
                cond = ((y1 > py) != (y2 > py)) and (
                    px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-6) + x1
                )
                if cond:
                    inside = not inside
            return inside

        refined: List[Dict] = []
        img_h, img_w = image.shape[:2]
        t_begin = time.time()
        triggers = 0
        refined_cnt = 0

        for det in person_detections:
            try:
                bbox = det.get("bbox", [0, 0, 0, 0])
                score = float(det.get("confidence", 1.0))
                x1, y1, x2, y2 = [int(v) for v in bbox]
                if x2 <= x1 or y2 <= y1:
                    refined.append(det)
                    continue

                # 触发条件：分数区间 + ROI（可选）
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                if not _in_range(score):
                    refined.append(det)
                    continue
                if isinstance(roi_poly, list) and len(roi_poly) >= 3:
                    if not _pt_in_poly(cx, cy, roi_poly):
                        refined.append(det)
                        continue

                triggers += 1

                # 在人框ROI上执行重检
                roi = image[y1:y2, x1:x2]
                if roi.size == 0:
                    refined.append(det)
                    continue

                res = self._cascade_model(roi)
                best = None
                for r in res:
                    boxes = getattr(r, "boxes", None)
                    if boxes is None:
                        continue
                    for b in boxes:
                        try:
                            if int(b.cls[0]) != 0:  # 仅person
                                continue
                            conf = float(b.conf[0].cpu().numpy())
                            bx1, by1, bx2, by2 = [float(v) for v in b.xyxy[0].cpu().numpy()]
                            if best is None or conf > best[0]:
                                best = (conf, bx1, by1, bx2, by2)
                        except Exception:
                            continue

                if best is None:
                    refined.append(det)
                    continue

                conf_h, bx1, by1, bx2, by2 = best
                # 映射回全图坐标
                gx1 = int(x1 + max(0.0, bx1))
                gy1 = int(y1 + max(0.0, by1))
                gx2 = int(x1 + min(float(x2 - x1), bx2))
                gy2 = int(y1 + min(float(y2 - y1), by2))
                if gx2 > gx1 and gy2 > gy1:
                    det = det.copy()
                    det["bbox"] = [gx1, gy1, gx2, gy2]
                    det["confidence"] = max(float(det.get("confidence", 0.0)), float(conf_h))
                    det["cascade_refined"] = True
                    refined_cnt += 1
                refined.append(det)
            except Exception:
                refined.append(det)

        self.cascade_stats["triggers"] += triggers
        self.cascade_stats["refined"] += refined_cnt
        self.cascade_stats["time_total"] += max(0.0, time.time() - t_begin)

        if triggers:
            logger.info(
                f"级联：触发={triggers}, 细化={refined_cnt}, 总耗时+={time.time() - t_begin:.3f}s"
            )

        return refined

    def _detect_persons(self, image: np.ndarray) -> List[Dict]:
        """人体检测 - 所有其他检测的基础

        Args:
            image: 输入图像

        Returns:
            List[Dict]: 人体检测结果列表

        Raises:
            RuntimeError: 当人体检测器未初始化或检测失败时
        """
        if self.human_detector is None:
            raise RuntimeError(
                "人体检测器未初始化。请检查：\n" "1. 检测服务是否正确启动\n" "2. 人体检测模型文件是否存在\n" "3. 系统依赖是否完整"
            )

        detections = self.human_detector.detect(image)
        return detections if detections else []

    def _detect_hairnet_for_persons(
        self, image: np.ndarray, person_detections: List[Dict]
    ) -> List[Dict]:
        """为检测到的人员进行发网检测

        Args:
            image: 输入图像
            person_detections: 人体检测结果列表

        Returns:
            List[Dict]: 发网检测结果列表

        Raises:
            RuntimeError: 当发网检测器未初始化时
        """
        if self.hairnet_detector is None:
            raise RuntimeError(
                "发网检测器未初始化。请检查：\n" "1. 检测服务是否正确启动\n" "2. 发网检测模型文件是否存在\n" "3. 系统依赖是否完整"
            )

        hairnet_results = []

        try:
            # 对于YOLOHairnetDetector，直接传递完整图像进行检测
            if hasattr(self.hairnet_detector, "detect_hairnet_compliance"):
                # 使用YOLOHairnetDetector的detect_hairnet_compliance方法，传递已有的人体检测结果避免重复检测
                compliance_result = self.hairnet_detector.detect_hairnet_compliance(
                    image, person_detections
                )

                # 从合规检测结果中提取每个人的发网信息
                detections = compliance_result.get("detections", [])

                for i, person_detection in enumerate(person_detections):
                    person_bbox = person_detection.get("bbox", [0, 0, 0, 0])

                    # 查找与该人员对应的发网检测结果
                    has_hairnet = False
                    hairnet_confidence = 0.0
                    hairnet_bbox = person_bbox

                    # 在合规检测结果中查找对应的人员
                    if i < len(detections):
                        detection_info = detections[i]
                        has_hairnet = detection_info.get("has_hairnet", False)
                        hairnet_confidence = detection_info.get(
                            "hairnet_confidence", 0.0
                        )
                        hairnet_bbox = detection_info.get("bbox", person_bbox)

                    # 计算头部区域坐标（用于显示）
                    x1, y1, x2, y2 = map(int, person_bbox)
                    head_height = int((y2 - y1) * 0.3)
                    head_y1 = max(0, y1)
                    head_y2 = min(image.shape[0], y1 + head_height)
                    head_x1 = max(0, x1)
                    head_x2 = min(image.shape[1], x2)

                    hairnet_results.append(
                        {
                            "person_id": i + 1,
                            "person_bbox": person_bbox,
                            "head_bbox": [head_x1, head_y1, head_x2, head_y2],
                            "has_hairnet": has_hairnet,
                            "hairnet_confidence": hairnet_confidence,
                            "hairnet_bbox": hairnet_bbox,
                        }
                    )
            else:
                # 对于传统的发网检测器，使用头部区域检测
                for i, detection in enumerate(person_detections):
                    try:
                        bbox = detection.get("bbox", [0, 0, 0, 0])
                        x1, y1, x2, y2 = map(int, bbox)

                        # 提取头部区域
                        head_height = int((y2 - y1) * 0.3)
                        head_y1 = max(0, y1)
                        head_y2 = min(image.shape[0], y1 + head_height)
                        head_x1 = max(0, x1)
                        head_x2 = min(image.shape[1], x2)

                        if head_y2 > head_y1 and head_x2 > head_x1:
                            head_region = image[head_y1:head_y2, head_x1:head_x2]
                            hairnet_result = (
                                self.hairnet_detector.detect_hairnet_compliance(
                                    head_region
                                )
                            )

                            hairnet_results.append(
                                {
                                    "person_id": i + 1,
                                    "person_bbox": bbox,
                                    "head_bbox": [head_x1, head_y1, head_x2, head_y2],
                                    "has_hairnet": hairnet_result.get(
                                        "wearing_hairnet", False
                                    ),
                                    "hairnet_confidence": hairnet_result.get(
                                        "confidence", 0.0
                                    ),
                                    "hairnet_bbox": hairnet_result.get(
                                        "head_roi_coords",
                                        [head_x1, head_y1, head_x2, head_y2],
                                    ),
                                }
                            )
                    except Exception as e:
                        logger.error(f"人员 {i+1} 发网检测失败: {e}")

        except Exception as e:
            logger.error(f"发网检测过程失败: {e}")

        return hairnet_results

    def _detect_handwash_for_persons(
        self, image: np.ndarray, person_detections: List[Dict]
    ) -> List[Dict]:
        """为检测到的人员进行洗手行为检测"""
        if self.behavior_recognizer is None:
            logger.warning("行为识别器未初始化，使用模拟结果")
            # 使用模拟结果，假设所有人都在洗手
            return [
                {
                    "person_id": i + 1,
                    "person_bbox": detection.get("bbox", [0, 0, 0, 0]),
                    "is_handwashing": True,  # 模拟所有人都在洗手
                    "handwashing": True,  # 兼容性字段
                    "handwash_confidence": 0.85,
                }
                for i, detection in enumerate(person_detections)
            ]

        handwash_results = []

        for i, detection in enumerate(person_detections):
            try:
                # 调用实际的洗手检测逻辑
                bbox = detection.get("bbox", [0, 0, 0, 0])
                x1, y1, x2, y2 = map(int, bbox)

                # 提取人体区域进行行为分析
                person_region = image[y1:y2, x1:x2]

                if person_region.size > 0:
                    # 使用行为识别器检测洗手行为
                    # 获取实际的手部区域信息
                    hand_regions = self._get_actual_hand_regions(image, bbox)

                    # 传递完整图像帧给行为识别器以支持MediaPipe检测
                    confidence = self.behavior_recognizer.detect_handwashing(
                        bbox, hand_regions, track_id=i + 1, frame=image
                    )
                    is_handwashing = (
                        confidence >= self.behavior_recognizer.confidence_threshold
                    )

                    # 添加调试日志
                    logger.info(
                        f"人员 {i+1} 洗手检测: 置信度={confidence:.3f}, 阈值={self.behavior_recognizer.confidence_threshold}, 结果={is_handwashing}"
                    )
                else:
                    is_handwashing = False
                    confidence = 0.0

                handwash_results.append(
                    {
                        "person_id": i + 1,
                        "person_bbox": bbox,
                        "is_handwashing": is_handwashing,
                        "handwashing": is_handwashing,  # 兼容性字段
                        "handwash_confidence": confidence,
                    }
                )
            except Exception as e:
                logger.error(f"人员 {i+1} 洗手检测失败: {e}")
                # 添加默认结果
                handwash_results.append(
                    {
                        "person_id": i + 1,
                        "person_bbox": detection.get("bbox", [0, 0, 0, 0]),
                        "is_handwashing": True,  # 默认假设在洗手
                        "handwashing": True,
                        "handwash_confidence": 0.5,
                    }
                )

        return handwash_results

    def _detect_sanitize_for_persons(
        self, image: np.ndarray, person_detections: List[Dict]
    ) -> List[Dict]:
        """为检测到的人员进行消毒行为检测"""
        if self.behavior_recognizer is None:
            logger.warning("行为识别器未初始化，使用模拟结果")
            # 使用模拟结果，假设所有人都在消毒
            return [
                {
                    "person_id": i + 1,
                    "person_bbox": detection.get("bbox", [0, 0, 0, 0]),
                    "is_sanitizing": True,  # 模拟所有人都在消毒
                    "sanitizing": True,  # 兼容性字段
                    "sanitize_confidence": 0.85,
                }
                for i, detection in enumerate(person_detections)
            ]

        sanitize_results = []

        for i, detection in enumerate(person_detections):
            try:
                # 调用实际的消毒检测逻辑
                bbox = detection.get("bbox", [0, 0, 0, 0])
                x1, y1, x2, y2 = map(int, bbox)

                # 提取人体区域进行行为分析
                person_region = image[y1:y2, x1:x2]

                if person_region.size > 0:
                    # 使用行为识别器检测消毒行为
                    # 获取实际的手部区域信息
                    hand_regions = self._get_actual_hand_regions(image, bbox)

                    # 传递完整图像帧给行为识别器以支持MediaPipe检测
                    confidence = self.behavior_recognizer.detect_sanitizing(
                        bbox, hand_regions, track_id=i + 1, frame=image
                    )
                    is_sanitizing = (
                        confidence >= self.behavior_recognizer.confidence_threshold
                    )
                else:
                    is_sanitizing = False
                    confidence = 0.0

                sanitize_results.append(
                    {
                        "person_id": i + 1,
                        "person_bbox": bbox,
                        "is_sanitizing": is_sanitizing,
                        "sanitizing": is_sanitizing,  # 兼容性字段
                        "sanitize_confidence": confidence,
                    }
                )
            except Exception as e:
                logger.error(f"人员 {i+1} 消毒检测失败: {e}")
                # 添加默认结果
                sanitize_results.append(
                    {
                        "person_id": i + 1,
                        "person_bbox": detection.get("bbox", [0, 0, 0, 0]),
                        "is_sanitizing": True,  # 默认假设在消毒
                        "sanitizing": True,
                        "sanitize_confidence": 0.5,
                    }
                )

        return sanitize_results

    def _estimate_hand_regions(self, person_bbox: List[int]) -> List[Dict]:
        """
        估算人体的手部区域，优先使用姿态检测器

        Args:
            person_bbox: 人体边界框 [x1, y1, x2, y2]

        Returns:
            手部区域列表
        """
        # 如果有姿态检测器，尝试使用实际的手部检测
        if self.pose_detector is not None:
            try:
                # 从人体区域提取图像进行手部检测
                x1, y1, x2, y2 = person_bbox
                # 这里需要完整图像，所以返回估算结果
                # 实际的手部检测在其他地方进行
                pass
            except Exception as e:
                logger.debug(f"姿态检测器手部检测失败，使用估算方法: {e}")

        # 使用估算方法
        x1, y1, x2, y2 = person_bbox
        width = x2 - x1
        height = y2 - y1

        # 估算手部大小（相对于人体尺寸）
        hand_box_h = int(0.15 * height)
        hand_box_w = int(0.25 * width)

        # 估算左右手位置（在人体中下部）
        hand_y = y1 + int(0.55 * height)

        left_hand_bbox = [x1, hand_y, x1 + hand_box_w, hand_y + hand_box_h]
        right_hand_bbox = [x2 - hand_box_w, hand_y, x2, hand_y + hand_box_h]

        return [{"bbox": left_hand_bbox}, {"bbox": right_hand_bbox}]

    def _get_actual_hand_regions(
        self, image: np.ndarray, person_bbox: List[int]
    ) -> List[Dict]:
        """
        获取实际的手部区域，优先使用姿态检测器

        Args:
            image: 完整图像
            person_bbox: 人体边界框 [x1, y1, x2, y2]

        Returns:
            手部区域列表
        """
        hand_regions = []

        # 如果有姿态检测器，优先在人框ROI上执行手部检测，并映射回全图坐标
        if self.pose_detector is not None:
            try:
                x1, y1, x2, y2 = [int(v) for v in person_bbox]
                # 外扩20%边距，并裁回图像范围
                w = x2 - x1
                h = y2 - y1
                pad_x = int(0.2 * w)
                pad_y = int(0.2 * h)
                x1 = max(0, x1 - pad_x)
                y1 = max(0, y1 - pad_y)
                x2 = min(image.shape[1], x2 + pad_x)
                y2 = min(image.shape[0], y2 + pad_y)

                if x2 > x1 and y2 > y1:
                    roi = image[y1:y2, x1:x2]
                    roi_h, roi_w = roi.shape[:2]

                    # 预处理：CLAHE增强亮度、轻度锐化
                    def _enhance(img: np.ndarray) -> np.ndarray:
                        try:
                            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                            l, a, b = cv2.split(lab)
                            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                            l2 = clahe.apply(l)
                            lab2 = cv2.merge((l2, a, b))
                            enhanced = cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)
                            # 轻度锐化
                            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
                            sharpened = cv2.filter2D(enhanced, -1, kernel)
                            return sharpened
                        except Exception:
                            return img

                    # 保证最小ROI边长，并做多尺度（1.0 和 1.25倍）
                    min_side_target = 160
                    base_scale = 1.0
                    min_side = max(1, min(roi_w, roi_h))
                    if min_side < min_side_target:
                        base_scale = float(min_side_target) / float(min_side)
                    scales = [base_scale, min(2.0, base_scale * 1.25)]

                    detected_any = False
                    for scale in scales:
                        # 缩放ROI
                        scaled_w = max(1, int(round(roi_w * scale)))
                        scaled_h = max(1, int(round(roi_h * scale)))
                        scaled_roi = cv2.resize(roi, (scaled_w, scaled_h), interpolation=cv2.INTER_CUBIC)
                        scaled_roi = _enhance(scaled_roi)

                        # 调用手部检测（在缩放ROI上）
                        roi_hands = self.pose_detector.detect_hands(scaled_roi)

                        for hres in roi_hands:
                            # 读取缩放ROI内的像素bbox，并映射回全图
                            bbox = hres.get("bbox", [0, 0, 0, 0])
                            bx1, by1, bx2, by2 = [int(b) for b in bbox]
                            # 先还原到原ROI坐标系
                            ox1 = bx1 / scale
                            oy1 = by1 / scale
                            ox2 = bx2 / scale
                            oy2 = by2 / scale
                            gx1, gy1 = int(round(x1 + ox1)), int(round(y1 + oy1))
                            gx2, gy2 = int(round(x1 + ox2)), int(round(y1 + oy2))

                            mapped = {
                                "bbox": [gx1, gy1, gx2, gy2],
                                "confidence": float(hres.get("confidence", 0.0)),
                            }

                            # 映射关键点（hres.landmarks 相对缩放ROI的归一化坐标）
                            if "landmarks" in hres and hres["landmarks"]:
                                mapped_landmarks = []
                                sw, sh = scaled_w, scaled_h
                                for lm in hres["landmarks"]:
                                    px = lm.get("x", 0.0) * sw  # 像素坐标（缩放ROI）
                                    py = lm.get("y", 0.0) * sh
                                    ox = px / scale  # 还原到原ROI像素
                                    oy = py / scale
                                    mapped_landmarks.append({
                                        "x": (x1 + ox) / image.shape[1],
                                        "y": (y1 + oy) / image.shape[0],
                                    })
                                mapped["landmarks"] = mapped_landmarks

                            # 透传来源与标签（若存在）
                            if "class_name" in hres:
                                mapped["class_name"] = hres["class_name"]
                            if "source" in hres:
                                mapped["source"] = hres["source"]

                            # 仅保留手中心在该人体框内的结果
                            cx = (gx1 + gx2) / 2
                            cy = (gy1 + gy2) / 2
                            if x1 <= cx <= x2 and y1 <= cy <= y2:
                                hand_regions.append(mapped)

                if hand_regions:
                    detected_any = True

                    if detected_any:
                        logger.debug(f"ROI手检检测到 {len(hand_regions)} 个手部区域 (多尺度/增强)")
                        return hand_regions

                # ROI为空或未检出时，退回整帧手检并过滤到该人体框
                full_hands = self.pose_detector.detect_hands(image)
                for hres in full_hands:
                    bbox = hres.get("bbox", [0, 0, 0, 0])
                    hx1, hy1, hx2, hy2 = [int(b) for b in bbox]
                    cx = (hx1 + hx2) / 2
                    cy = (hy1 + hy2) / 2
                    if x1 <= cx <= x2 and y1 <= cy <= y2:
                        hand_regions.append(hres)

                if hand_regions:
                    logger.debug(f"整帧手检过滤到 {len(hand_regions)} 个手部区域")
                    return hand_regions

            except Exception as e:
                logger.debug(f"姿态检测器手部检测失败，使用估算方法: {e}")

        # 回退到估算方法
        estimated_regions = self._estimate_hand_regions(person_bbox)
        logger.debug("使用估算的手部区域")
        return estimated_regions

    # --- Public helper for external callers (e.g., tracking-driven pipelines) ---
    def get_hand_regions_for_person(self, image: np.ndarray, person_bbox: List[int]) -> List[Dict]:
        """对外公开：根据人体框返回手部区域（可能包含landmarks与来源）"""
        return self._get_actual_hand_regions(image, person_bbox)

    def _create_annotated_image(
        self,
        image: np.ndarray,
        person_detections: List[Dict],
        hairnet_results: List[Dict],
        handwash_results: List[Dict],
        sanitize_results: List[Dict],
    ) -> np.ndarray:
        """创建带注释的结果图像"""
        annotated = image.copy()

        try:
            # 绘制人体检测框
            for detection in person_detections:
                bbox = detection.get("bbox", [0, 0, 0, 0])
                x1, y1, x2, y2 = map(int, bbox)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # 留空，由上层统一中文渲染

            # 绘制发网检测结果
            for result in hairnet_results:
                head_bbox = result.get("head_bbox", [0, 0, 0, 0])
                x1, y1, x2, y2 = map(int, head_bbox)
                color = (0, 255, 0) if result.get("has_hairnet", False) else (0, 0, 255)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

                # 留空，由上层统一中文渲染

            # 绘制洗手检测结果
            for result in handwash_results:
                if result.get("is_handwashing", False):
                    person_bbox = result.get("person_bbox", [0, 0, 0, 0])
                    x1, y1, x2, y2 = map(int, person_bbox)
                    # 在人体框上方绘制洗手标签
                    # 留空，由上层统一中文渲染

            # 绘制消毒检测结果
            for result in sanitize_results:
                if result.get("is_sanitizing", False):
                    person_bbox = result.get("person_bbox", [0, 0, 0, 0])
                    x1, y1, x2, y2 = map(int, person_bbox)
                    # 在人体框上方绘制消毒标签
                    # 留空，由上层统一中文渲染

            # 手部可视化：无论是否检测到人体，都尝试绘制手部（便于手部近景视频调试）
            hands_count = 0
            if self.pose_detector is not None:
                hands_results = []
                if hasattr(self.pose_detector, "detect_hands"):
                    hands_results = self.pose_detector.detect_hands(image)

                hands_count = len(hands_results)

                # 绘制手部：优先绘制bbox与来源标签；如有关键点则再绘制骨架
                for hand_result in hands_results:
                    bbox = hand_result.get("bbox", [0, 0, 0, 0])
                    hx1, hy1, hx2, hy2 = map(int, bbox)
                    label = hand_result.get("class_name", "hand")
                    src = hand_result.get("source", "auto")

                    # 绘制手部边界框与来源
                    cv2.rectangle(annotated, (hx1, hy1), (hx2, hy2), (255, 255, 0), 2)
                    cv2.putText(
                        annotated,
                        f"Hand: {label} [{src}]",
                        (hx1, hy1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 0),
                        2,
                    )

                    # 若有关键点则绘制骨架
                    if "landmarks" in hand_result and hand_result["landmarks"]:
                        landmarks = hand_result["landmarks"]
                        h, w = image.shape[:2]
                        for i, landmark in enumerate(landmarks):
                            x = int(landmark["x"] * w)
                            y = int(landmark["y"] * h)
                            cv2.circle(annotated, (x, y), 3, (0, 255, 255), -1)

                        if len(landmarks) >= 21:
                            wrist = (
                                int(landmarks[0]["x"] * w),
                                int(landmarks[0]["y"] * h),
                            )
                            finger_bases = [5, 9, 13, 17]
                            for base_idx in finger_bases:
                                if base_idx < len(landmarks):
                                    base = (
                                        int(landmarks[base_idx]["x"] * w),
                                        int(landmarks[base_idx]["y"] * h),
                                    )
                                    cv2.line(annotated, wrist, base, (0, 255, 255), 1)

                            finger_connections = [
                                [1, 2, 3, 4],
                                [5, 6, 7, 8],
                                [9, 10, 11, 12],
                                [13, 14, 15, 16],
                                [17, 18, 19, 20],
                            ]

                            for finger in finger_connections:
                                for j in range(len(finger) - 1):
                                    if finger[j] < len(landmarks) and finger[j + 1] < len(landmarks):
                                        pt1 = (
                                            int(landmarks[finger[j]]["x"] * w),
                                            int(landmarks[finger[j]]["y"] * h),
                                        )
                                        pt2 = (
                                            int(landmarks[finger[j + 1]]["x"] * w),
                                            int(landmarks[finger[j + 1]]["y"] * h),
                                        )
                                        cv2.line(annotated, pt1, pt2, (0, 255, 255), 1)

            # 在左上角显示帧信息
            # 顶层渲染中文信息

        except Exception as e:
            logger.error(f"图像注释失败: {e}")

        return annotated

    def get_statistics(self) -> Dict[str, Any]:
        """获取管道统计信息"""
        stats = self.stats.copy()

        if self.enable_cache and self.frame_cache is not None:
            cache_stats = self.frame_cache.get_stats()
            stats.update(
                {
                    "cache_stats": cache_stats,
                    "cache_hit_rate": (
                        self.stats["cache_hits"]
                        / max(1, self.stats["cache_hits"] + self.stats["cache_misses"])
                    ),
                }
            )

        return stats

    def clear_cache(self):
        """清空缓存"""
        if self.enable_cache and self.frame_cache is not None:
            self.frame_cache.clear()

    def update_models(
        self, human_detector=None, hairnet_detector=None, behavior_recognizer=None
    ):
        """更新模型（热更新支持）"""
        if human_detector is not None:
            self.human_detector = human_detector
            logger.info("人体检测器已更新")

        if hairnet_detector is not None:
            self.hairnet_detector = hairnet_detector
            logger.info("发网检测器已更新")

        if behavior_recognizer is not None:
            self.behavior_recognizer = behavior_recognizer
            logger.info("行为识别器已更新")

        # 清空缓存以确保使用新模型
        self.clear_cache()


class VideoStreamOptimizer:
    """视频流处理优化器 - 专门用于视频流的优化处理"""

    def __init__(
        self,
        detection_pipeline: OptimizedDetectionPipeline,
        frame_skip: int = 3,  # 每3帧处理一次
        similarity_threshold: float = 0.95,
    ):  # 帧相似度阈值
        self.detection_pipeline = detection_pipeline
        self.frame_skip = frame_skip
        self.similarity_threshold = similarity_threshold

        self.frame_count = 0
        self.last_processed_frame = None
        self.last_result = None

        logger.info(f"视频流优化器初始化: 跳帧={frame_skip}, 相似度阈值={similarity_threshold}")

    def process_frame(
        self, frame: np.ndarray, force_process: bool = False
    ) -> Optional[DetectionResult]:
        """处理视频帧（带优化）"""
        self.frame_count += 1

        # 跳帧优化
        if not force_process and self.frame_count % self.frame_skip != 0:
            return self.last_result

        # 帧相似度检查
        if not force_process and self.last_processed_frame is not None:
            similarity = self._calculate_frame_similarity(
                frame, self.last_processed_frame
            )
            if similarity > self.similarity_threshold:
                logger.debug(f"帧相似度过高 ({similarity:.3f})，跳过处理")
                return self.last_result

        # 执行检测
        result = self.detection_pipeline.detect_comprehensive(frame)

        # 更新状态
        self.last_processed_frame = frame.copy()
        self.last_result = result

        return result

    def _calculate_frame_similarity(
        self, frame1: np.ndarray, frame2: np.ndarray
    ) -> float:
        """计算两帧之间的相似度"""
        try:
            # 转换为灰度图
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

            # 计算结构相似性
            # 这里使用简单的均方误差作为相似度度量
            mse = np.mean((gray1.astype(float) - gray2.astype(float)) ** 2)
            max_mse = 255.0**2
            similarity = 1.0 - (mse / max_mse)

            return float(similarity)
        except Exception as e:
            logger.error(f"计算帧相似度失败: {e}")
            return 0.0
