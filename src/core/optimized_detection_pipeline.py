#!/usr/bin/env python3
"""
优化的检测管道 - 实现模型复用、缓存和统一处理

主要优化点：
1. 模型加载移至初始化阶段，避免重复加载
2. 构建统一的BehaviorDetectionPipeline，复用中间结果
3. 明确检测顺序和依赖关系
4. 增加缓存机制，特别是视频流处理
"""

import asyncio
import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from src.config.unified_params import get_unified_params
from src.detection.pose_detector import PoseDetectorFactory

# 导入FrameMetadata相关类（可选，用于状态管理和异步处理）
try:
    from src.core.async_detection_pipeline import AsyncDetectionPipeline
    from src.core.frame_metadata import FrameMetadata, FrameSource
    from src.core.frame_metadata_manager import FrameMetadataManager
    from src.core.state_manager import StateManager

    FRAME_METADATA_AVAILABLE = True
except ImportError:
    FRAME_METADATA_AVAILABLE = False
    FrameMetadata = None
    FrameSource = None
    FrameMetadataManager = None
    StateManager = None
    AsyncDetectionPipeline = None

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
    hand_regions: Optional[List[Dict]] = None
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
        # 使用帧的形状和固定步长采样生成稳定哈希
        h, w = frame.shape[:2]
        if h == 0 or w == 0:
            return f"{h}x{w}_empty"

        if h < 10 or w < 10:
            sampled = frame
        else:
            sampled = frame[::10, ::10]

        if sampled.size == 0:
            sampled = frame

        hasher = hashlib.md5()
        hasher.update(f"{h}x{w}_{frame.dtype}".encode("utf-8"))
        hasher.update(sampled.tobytes())
        return f"{h}x{w}_{hasher.hexdigest()}"

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
        enable_state_management: bool = True,  # 是否启用状态管理
        frame_metadata_manager: Optional[
            FrameMetadataManager
        ] = None,  # 可选的FrameMetadataManager
        enable_async: bool = False,  # 是否启用异步检测（任务1.3）
        max_workers: int = 2,  # 异步检测的最大工作线程数
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

        # 如果没有提供人体检测器，尝试初始化一个默认的
        if self.human_detector is None:
            try:
                from src.detection.detector import HumanDetector

                self.human_detector = HumanDetector()
                logger.info("默认人体检测器初始化成功")
            except Exception as e:
                logger.warning(f"默认人体检测器初始化失败: {e}")
                self.human_detector = None

        # 初始化姿态检测器
        if pose_detector is not None:
            self.pose_detector = pose_detector
            logger.info("姿态检测器 (外部提供) 初始化成功")
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

        # 状态管理相关（任务1.1）
        self.enable_state_management = (
            enable_state_management and FRAME_METADATA_AVAILABLE
        )
        if self.enable_state_management:
            # 初始化FrameMetadataManager（与任务1.3共享）
            self.frame_metadata_manager = (
                frame_metadata_manager
                or FrameMetadataManager(max_history=1000, sync_window=0.1)
            )

            # 初始化StateManager
            params = get_unified_params()
            state_params = getattr(params, "state_management", None)
            if state_params:
                stability_frames = getattr(state_params, "stability_frames", 5)
                confidence_threshold = getattr(
                    state_params, "confidence_threshold", 0.7
                )
            else:
                stability_frames = 5
                confidence_threshold = 0.7

            self.state_manager = StateManager(
                stability_frames=stability_frames,
                confidence_threshold=confidence_threshold,
                frame_metadata_manager=self.frame_metadata_manager,
            )
            logger.info("状态管理已启用")
        else:
            self.frame_metadata_manager = None
            self.state_manager = None
            if enable_state_management:
                logger.warning("状态管理被请求但FrameMetadata不可用，已禁用")

        # 保存统一参数配置（用于可视化置信度阈值）
        try:
            self.params = get_unified_params()
        except Exception as e:
            logger.warning(f"加载统一参数配置失败: {e}，使用默认值")
            self.params = None

        # 异步检测相关（任务1.3）
        self.enable_async = enable_async and FRAME_METADATA_AVAILABLE
        if self.enable_async:
            if AsyncDetectionPipeline is None:
                logger.warning("异步检测被请求但AsyncDetectionPipeline不可用，已禁用")
                self.enable_async = False
                self.async_pipeline = None
            else:
                # 初始化AsyncDetectionPipeline（共享FrameMetadataManager）
                self.async_pipeline = AsyncDetectionPipeline(
                    human_detector=self.human_detector,
                    hairnet_detector=self.hairnet_detector,
                    pose_detector=self.pose_detector,
                    behavior_recognizer=self.behavior_recognizer,
                    frame_metadata_manager=self.frame_metadata_manager,  # 共享
                    max_workers=max_workers,
                )
                logger.info(f"异步检测已启用: max_workers={max_workers}")
        else:
            self.async_pipeline = None
            if enable_async:
                logger.warning("异步检测被请求但FrameMetadata不可用，已禁用")

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
        camera_id: str = "default",  # 用于FrameMetadata
    ) -> DetectionResult:
        """
        综合检测 - 统一入口点

        Args:
            image: 输入图像
            enable_hairnet: 是否启用发网检测
            enable_handwash: 是否启用洗手检测
            enable_sanitize: 是否启用消毒检测
            force_refresh: 是否强制刷新（忽略缓存）
            camera_id: 摄像头ID（用于FrameMetadata）

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

        # 执行检测流水线（支持异步和同步两种模式）
        if self.enable_async and self.async_pipeline:
            # 使用异步检测（任务1.3）
            result = self._execute_detection_pipeline_async(
                image, camera_id, enable_hairnet, enable_handwash, enable_sanitize
            )
        else:
            # 使用同步检测（原有逻辑）
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

    def _execute_detection_pipeline_async(
        self,
        image: np.ndarray,
        camera_id: str,
        enable_hairnet: bool,
        enable_handwash: bool,
        enable_sanitize: bool,
    ) -> DetectionResult:
        """
        使用异步检测管道执行检测

        Args:
            image: 输入图像
            camera_id: 摄像头ID
            enable_hairnet: 是否启用发网检测
            enable_handwash: 是否启用洗手检测
            enable_sanitize: 是否启用消毒检测

        Returns:
            DetectionResult: 综合检测结果
        """
        # 创建FrameMetadata
        frame_meta = self.frame_metadata_manager.create_frame_metadata(
            frame=image, camera_id=camera_id, source=FrameSource.REALTIME_STREAM
        )

        # 执行异步检测
        frame_meta = asyncio.run(
            self.async_pipeline.detect_comprehensive_async(
                frame_meta, enable_hairnet, enable_handwash, enable_sanitize
            )
        )

        # 应用状态稳定判定（任务1.1）
        if self.enable_state_management and self.state_manager:
            for hairnet_result in frame_meta.hairnet_results:
                hairnet_confidence = hairnet_result.get("hairnet_confidence", 0.0)
                has_hairnet = hairnet_result.get("has_hairnet", False)

                # 如果未佩戴发网，使用置信度作为违规置信度
                if has_hairnet is False:
                    violation_confidence = hairnet_confidence
                else:
                    violation_confidence = 0.0

                self.state_manager.update_state(frame_meta, violation_confidence)

        # 转换为DetectionResult（向后兼容）
        # 传递原始图像用于创建可视化图片
        return self._frame_meta_to_detection_result(frame_meta, image)

    def _frame_meta_to_detection_result(
        self,
        frame_meta: FrameMetadata,
        image: Optional[np.ndarray] = None,
    ) -> DetectionResult:
        """
        将FrameMetadata转换为DetectionResult（向后兼容）

        Args:
            frame_meta: 帧元数据
            image: 原始图像（用于创建可视化图片，如果frame_meta.frame为None）

        Returns:
            DetectionResult: 检测结果
        """
        # 计算处理时间
        processing_times = frame_meta.processing_times.copy()
        if "total" not in processing_times:
            processing_times["total"] = sum(processing_times.values())

        # 创建可视化图片（如果原始图像可用）
        annotated_image = None
        source_image = frame_meta.frame if frame_meta.frame is not None else image
        if source_image is not None:
            try:
                # 从配置中获取可视化最小置信度阈值（默认0.5）
                min_confidence = 0.5
                if hasattr(self, "params") and self.params is not None:
                    # 使用人体检测置信度阈值作为可视化阈值，但不低于0.5
                    human_conf = self.params.human_detection.confidence_threshold
                    min_confidence = max(0.5, human_conf)

                annotated_image = self._create_annotated_image(
                    source_image,
                    frame_meta.person_detections,
                    frame_meta.hairnet_results,
                    frame_meta.handwash_results,
                    frame_meta.sanitize_results,
                    hand_regions=None,
                    min_confidence=min_confidence,  # 传递可视化置信度阈值
                )
            except Exception as e:
                logger.warning(f"创建可视化图片失败: {e}", exc_info=True)

        return DetectionResult(
            person_detections=frame_meta.person_detections,
            hairnet_results=frame_meta.hairnet_results,
            handwash_results=frame_meta.handwash_results,
            sanitize_results=frame_meta.sanitize_results,
            processing_times=processing_times,
            hand_regions=None,
            annotated_image=annotated_image,
            frame_cache_key=frame_meta.frame_hash,
        )

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
            logger.debug(
                f"🔵 开始发网检测: 人数={len(person_detections)}, "
                f"hairnet_detector={'存在' if self.hairnet_detector else '不存在'}, "
                f"类型={type(self.hairnet_detector).__name__ if self.hairnet_detector else 'None'}"
            )
            hairnet_results = self._detect_hairnet_for_persons(image, person_detections)
            processing_times["hairnet_detection"] = time.time() - hairnet_start
            logger.debug(
                f"🔵 发网检测完成: 处理了 {len(hairnet_results)} 个人, "
                f"耗时={processing_times['hairnet_detection']:.3f}s"
            )

            # 应用状态稳定判定（任务1.1）
            if self.enable_state_management and self.state_manager:
                state_start = time.time()
                hairnet_results = self._apply_state_management_to_hairnet_results(
                    hairnet_results, image
                )
                processing_times["state_management"] = time.time() - state_start
        else:
            processing_times["hairnet_detection"] = 0.0

        # 阶段3: 行为检测（基于人体检测结果）
        handwash_results = []
        sanitize_results = []
        hand_regions_map: Dict[int, List[Dict]] = {}
        hand_regions_flat: List[Dict] = []

        if (enable_handwash or enable_sanitize) and len(person_detections) > 0:
            behavior_start = time.time()

            # 预计算手部区域，避免重复推理
            for i, detection in enumerate(person_detections):
                person_id = i + 1
                bbox = detection.get("bbox", [0, 0, 0, 0])
                regions = self._get_actual_hand_regions(image, bbox)
                hand_regions_map[person_id] = regions
                for region in regions:
                    region_with_id = region.copy()
                    region_with_id["person_id"] = person_id
                    hand_regions_flat.append(region_with_id)

            if enable_handwash:
                handwash_results = self._detect_handwash_for_persons(
                    image, person_detections, hand_regions_map=hand_regions_map
                )

            if enable_sanitize:
                sanitize_results = self._detect_sanitize_for_persons(
                    image, person_detections, hand_regions_map=hand_regions_map
                )

            processing_times["behavior_detection"] = time.time() - behavior_start
            logger.info(
                f"行为检测完成: 洗手={len(handwash_results)}, 消毒={len(sanitize_results)}, "
                f"人员数={len(person_detections)}, 耗时={processing_times['behavior_detection']:.3f}s"
            )
        else:
            processing_times["behavior_detection"] = 0.0

        # 阶段4: 结果可视化（可选）
        viz_start = time.time()
        # 从配置中获取可视化最小置信度阈值（默认0.5）
        min_confidence = 0.5
        if hasattr(self, "params") and self.params is not None:
            # 使用人体检测置信度阈值作为可视化阈值，但不低于0.5
            human_conf = self.params.human_detection.confidence_threshold
            min_confidence = max(0.5, human_conf)

        annotated_image = self._create_annotated_image(
            image,
            person_detections,
            hairnet_results,
            handwash_results,
            sanitize_results,
            hand_regions=hand_regions_flat,
            min_confidence=min_confidence,  # 传递可视化置信度阈值
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
            hand_regions=hand_regions_flat,
            annotated_image=annotated_image,
        )

    def _apply_state_management_to_hairnet_results(
        self,
        hairnet_results: List[Dict],
        image: np.ndarray,
        camera_id: str = "default",
    ) -> List[Dict]:
        """
        对发网检测结果应用状态管理

        Args:
            hairnet_results: 发网检测结果列表
            image: 输入图像
            camera_id: 摄像头ID

        Returns:
            更新后的发网检测结果列表（包含稳定状态信息）
        """
        if not self.enable_state_management or not self.state_manager:
            return hairnet_results

        updated_results = []

        for hairnet_result in hairnet_results:
            # 获取track_id（从hairnet_result或person_id）
            track_id = (
                hairnet_result.get("track_id")
                or f"person_{hairnet_result.get('person_id', 0)}"
            )

            # 创建FrameMetadata（简化处理，实际应该使用统一的frame_meta）
            from datetime import datetime

            frame_meta = FrameMetadata(
                frame_id=f"{camera_id}_{time.time():.6f}",
                timestamp=datetime.utcnow(),
                camera_id=camera_id,
                source=FrameSource.REALTIME_STREAM,
                frame=image,
                metadata={"track_id": track_id},
                hairnet_results=[hairnet_result],
            )

            # 获取发网置信度
            hairnet_confidence = hairnet_result.get("hairnet_confidence", 0.0)
            has_hairnet = hairnet_result.get("has_hairnet", False)

            # 如果未佩戴发网，使用置信度作为违规置信度；如果佩戴，违规置信度为0
            if has_hairnet is False:
                violation_confidence = hairnet_confidence
            else:
                violation_confidence = 0.0

            # 更新状态
            stable_state, stable_confidence = self.state_manager.update_state(
                frame_meta, violation_confidence
            )

            # 更新hairnet_result
            hairnet_result["stable_state"] = stable_state
            hairnet_result["stable_confidence"] = stable_confidence
            updated_results.append(hairnet_result)

        return updated_results

    # ----------------------- 级联逻辑 -----------------------
    def _cascade_refine_persons(
        self, image: np.ndarray, person_detections: List[Dict]
    ) -> List[Dict]:
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
                return lo <= float(score) <= hi
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
                            bx1, by1, bx2, by2 = [
                                float(v) for v in b.xyxy[0].cpu().numpy()
                            ]
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
                    det["confidence"] = max(
                        float(det.get("confidence", 0.0)), float(conf_h)
                    )
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
                logger.debug(
                    f"🔵 调用YOLOHairnetDetector.detect_hairnet_compliance: "
                    f"人数={len(person_detections)}, 图像大小={image.shape}"
                )
                # 使用YOLOHairnetDetector的detect_hairnet_compliance方法，传递已有的人体检测结果避免重复检测
                compliance_result = self.hairnet_detector.detect_hairnet_compliance(
                    image, person_detections
                )
                logger.debug(
                    f"🔵 YOLOHairnetDetector返回结果: "
                    f"total_persons={compliance_result.get('total_persons', 0)}, "
                    f"persons_with_hairnet={compliance_result.get('persons_with_hairnet', 0)}, "
                    f"detections数量={len(compliance_result.get('detections', []))}"
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
                    # 优化：使用35%高度，与YOLOHairnetDetector保持一致
                    x1, y1, x2, y2 = map(int, person_bbox)
                    person_height = y2 - y1
                    person_width = x2 - x1
                    head_height = int(person_height * 0.35)  # 从30%增加到35%
                    padding_height = int(head_height * 0.2)  # 20%padding
                    padding_width = int(person_width * 0.1)  # 10%padding宽度

                    head_y1 = max(0, y1 - padding_height)
                    head_y2 = min(image.shape[0], y1 + head_height + padding_height)
                    head_x1 = max(0, x1 - padding_width)
                    head_x2 = min(image.shape[1], x2 + padding_width)

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
                        # 优化：使用35%高度，与YOLOHairnetDetector保持一致
                        person_height = y2 - y1
                        person_width = x2 - x1
                        head_height = int(person_height * 0.35)  # 从30%增加到35%
                        padding_height = int(head_height * 0.2)  # 20%padding
                        padding_width = int(person_width * 0.1)  # 10%padding宽度

                        head_y1 = max(0, y1 - padding_height)
                        head_y2 = min(image.shape[0], y1 + head_height + padding_height)
                        head_x1 = max(0, x1 - padding_width)
                        head_x2 = min(image.shape[1], x2 + padding_width)

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
        self,
        image: np.ndarray,
        person_detections: List[Dict],
        hand_regions_map: Optional[Dict[int, List[Dict]]] = None,
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
                    if hand_regions_map is not None:
                        hand_regions = hand_regions_map.get(i + 1, [])
                    else:
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
        self,
        image: np.ndarray,
        person_detections: List[Dict],
        hand_regions_map: Optional[Dict[int, List[Dict]]] = None,
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
                    if hand_regions_map is not None:
                        hand_regions = hand_regions_map.get(i + 1, [])
                    else:
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
            except Exception as e:
                logger.info(f"姿态检测器手部检测失败，使用估算方法: {e}")

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
                            kernel = np.array(
                                [[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32
                            )
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
                        scaled_roi = cv2.resize(
                            roi, (scaled_w, scaled_h), interpolation=cv2.INTER_CUBIC
                        )
                        scaled_roi = _enhance(scaled_roi)

                        # 调用手部检测（在缩放ROI上）- 检查方法是否存在
                        roi_hands = []
                        if hasattr(self.pose_detector, "detect_hands"):
                            try:
                                roi_hands = self.pose_detector.detect_hands(scaled_roi)
                            except Exception as e:
                                logger.debug(f"ROI手部检测失败: {e}")
                                roi_hands = []
                        else:
                            # YOLOv8PoseDetector 没有 detect_hands 方法，使用姿态关键点提取手部区域
                            roi_hands = self._extract_hand_regions_from_pose(
                                scaled_roi, person_bbox
                            )

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
                                    mapped_landmarks.append(
                                        {
                                            "x": (x1 + ox) / image.shape[1],
                                            "y": (y1 + oy) / image.shape[0],
                                        }
                                    )
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
                        logger.info(
                            f"ROI手检检测到 {len(hand_regions)} 个手部区域 (多尺度/增强), person_bbox={person_bbox}"
                        )
                        return hand_regions

                # ROI为空或未检出时，退回整帧手检并过滤到该人体框
                full_hands = []
                if hasattr(self.pose_detector, "detect_hands"):
                    try:
                        full_hands = self.pose_detector.detect_hands(image)
                    except Exception as e:
                        logger.debug(f"整帧手部检测失败: {e}")
                        full_hands = []
                else:
                    # YOLOv8PoseDetector 没有 detect_hands 方法，使用姿态关键点提取手部区域
                    full_hands = self._extract_hand_regions_from_pose(
                        image, person_bbox
                    )
                for hres in full_hands:
                    bbox = hres.get("bbox", [0, 0, 0, 0])
                    hx1, hy1, hx2, hy2 = [int(b) for b in bbox]
                    cx = (hx1 + hx2) / 2
                    cy = (hy1 + hy2) / 2
                    if x1 <= cx <= x2 and y1 <= cy <= y2:
                        hand_regions.append(hres)

                if hand_regions:
                    logger.info(
                        f"整帧手检过滤到 {len(hand_regions)} 个手部区域, person_bbox={person_bbox}"
                    )
                    return hand_regions

            except Exception as e:
                logger.info(f"姿态检测器手部检测失败，使用估算方法: {e}")

        # 回退到估算方法
        estimated_regions = self._estimate_hand_regions(person_bbox)
        logger.info(
            f"使用估算的手部区域, person_bbox={person_bbox}, 估算手部数={len(estimated_regions)}"
        )
        return estimated_regions

    def _extract_hand_regions_from_pose(
        self, image: np.ndarray, person_bbox: List[int]
    ) -> List[Dict]:
        """
        从姿态关键点中提取手部区域（适用于YOLOv8PoseDetector）

        Args:
            image: 输入图像
            person_bbox: 人体边界框 [x1, y1, x2, y2]

        Returns:
            手部区域列表
        """
        hand_regions = []

        if self.pose_detector is None:
            return hand_regions

        try:
            # 使用姿态检测器检测人体关键点
            pose_detections = self.pose_detector.detect(image)

            x1, y1, x2, y2 = [int(v) for v in person_bbox]
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            # 找到最接近的人体姿态检测结果
            best_pose = None
            min_distance = float("inf")

            for pose in pose_detections:
                pose_bbox = pose.get("bbox", [0, 0, 0, 0])
                px1, py1, px2, py2 = pose_bbox
                pcx = (px1 + px2) / 2
                pcy = (py1 + py2) / 2
                distance = ((cx - pcx) ** 2 + (cy - pcy) ** 2) ** 0.5

                if distance < min_distance:
                    min_distance = distance
                    best_pose = pose

            if best_pose and "keypoints" in best_pose:
                keypoints = best_pose["keypoints"]
                if "xy" in keypoints and "conf" in keypoints:
                    kpts_xy = np.array(keypoints["xy"])
                    kpts_conf = np.array(keypoints["conf"])

                    # COCO姿态关键点索引：
                    # 9: 左手腕 (left_wrist)
                    # 10: 右手腕 (right_wrist)
                    # 7: 左肘 (left_elbow)
                    # 8: 右肘 (right_elbow)

                    left_wrist_idx = 9
                    right_wrist_idx = 10
                    left_elbow_idx = 7
                    right_elbow_idx = 8

                    # 提取左手区域
                    if (
                        left_wrist_idx < len(kpts_xy)
                        and left_elbow_idx < len(kpts_xy)
                        and kpts_conf[left_wrist_idx] > 0.3
                        and kpts_conf[left_elbow_idx] > 0.3
                    ):
                        wrist = kpts_xy[left_wrist_idx]
                        elbow = kpts_xy[left_elbow_idx]

                        # 估算手部区域（以手腕为中心，大小基于肘部到手腕的距离）
                        hand_size = np.linalg.norm(wrist - elbow) * 0.8
                        hand_w = int(hand_size)
                        hand_h = int(hand_size)

                        hand_x1 = max(0, int(wrist[0] - hand_w / 2))
                        hand_y1 = max(0, int(wrist[1] - hand_h / 2))
                        hand_x2 = min(image.shape[1], int(wrist[0] + hand_w / 2))
                        hand_y2 = min(image.shape[0], int(wrist[1] + hand_h / 2))

                        # 检查手部中心是否在人体框内
                        if x1 <= wrist[0] <= x2 and y1 <= wrist[1] <= y2:
                            hand_regions.append(
                                {
                                    "bbox": [hand_x1, hand_y1, hand_x2, hand_y2],
                                    "confidence": float(kpts_conf[left_wrist_idx]),
                                    "landmarks": [
                                        {
                                            "x": wrist[0] / image.shape[1],
                                            "y": wrist[1] / image.shape[0],
                                        }
                                    ],
                                    "source": "yolov8_pose_keypoints",
                                    "hand_label": "left",
                                }
                            )

                    # 提取右手区域
                    if (
                        right_wrist_idx < len(kpts_xy)
                        and right_elbow_idx < len(kpts_xy)
                        and kpts_conf[right_wrist_idx] > 0.3
                        and kpts_conf[right_elbow_idx] > 0.3
                    ):
                        wrist = kpts_xy[right_wrist_idx]
                        elbow = kpts_xy[right_elbow_idx]

                        # 估算手部区域
                        hand_size = np.linalg.norm(wrist - elbow) * 0.8
                        hand_w = int(hand_size)
                        hand_h = int(hand_size)

                        hand_x1 = max(0, int(wrist[0] - hand_w / 2))
                        hand_y1 = max(0, int(wrist[1] - hand_h / 2))
                        hand_x2 = min(image.shape[1], int(wrist[0] + hand_w / 2))
                        hand_y2 = min(image.shape[0], int(wrist[1] + hand_h / 2))

                        # 检查手部中心是否在人体框内
                        if x1 <= wrist[0] <= x2 and y1 <= wrist[1] <= y2:
                            hand_regions.append(
                                {
                                    "bbox": [hand_x1, hand_y1, hand_x2, hand_y2],
                                    "confidence": float(kpts_conf[right_wrist_idx]),
                                    "landmarks": [
                                        {
                                            "x": wrist[0] / image.shape[1],
                                            "y": wrist[1] / image.shape[0],
                                        }
                                    ],
                                    "source": "yolov8_pose_keypoints",
                                    "hand_label": "right",
                                }
                            )

                    if hand_regions:
                        logger.info(
                            f"从姿态关键点提取到 {len(hand_regions)} 个手部区域, person_bbox={person_bbox}"
                        )

        except Exception as e:
            logger.debug(f"从姿态关键点提取手部区域失败: {e}")

        return hand_regions

    # --- Public helper for external callers (e.g., tracking-driven pipelines) ---
    def get_hand_regions_for_person(
        self, image: np.ndarray, person_bbox: List[int]
    ) -> List[Dict]:
        """对外公开：根据人体框返回手部区域（可能包含landmarks与来源）"""
        return self._get_actual_hand_regions(image, person_bbox)

    def _create_annotated_image(
        self,
        image: np.ndarray,
        person_detections: List[Dict],
        hairnet_results: List[Dict],
        handwash_results: List[Dict],
        sanitize_results: List[Dict],
        hand_regions: Optional[List[Dict]] = None,
        min_confidence: float = 0.5,  # 可视化最小置信度阈值
    ) -> np.ndarray:
        """创建带注释的结果图像

        Args:
            image: 输入图像
            person_detections: 人体检测结果列表
            hairnet_results: 发网检测结果列表
            handwash_results: 洗手检测结果列表
            sanitize_results: 消毒检测结果列表
            hand_regions: 预计算的手部区域列表（避免重复推理）
            min_confidence: 可视化最小置信度阈值（默认0.5，过滤低置信度检测）

        Returns:
            带注释的图像
        """
        annotated = image.copy()

        try:
            # 过滤低置信度的人体检测（只显示高置信度的检测）
            filtered_person_detections = [
                det
                for det in person_detections
                if det.get("confidence", 0.0) >= min_confidence
            ]

            # 绘制人体检测框
            for detection in filtered_person_detections:
                bbox = detection.get("bbox", [0, 0, 0, 0])
                x1, y1, x2, y2 = map(int, bbox)
                confidence = detection.get("confidence", 0.0)
                track_id = detection.get("track_id")

                # 绘制人体边界框（绿色）
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # 绘制标签
                label = f"Person {confidence:.2f}"
                if track_id is not None:
                    label += f" ID:{track_id}"
                cv2.putText(
                    annotated,
                    label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2,
                )

            # 发网检测使用更低的置信度阈值（因为发网检测本身置信度可能较低）
            # 使用发网检测的置信度阈值，但不低于0.2（确保能看到更多检测结果）
            hairnet_min_confidence = 0.2  # 从0.3降低到0.2，提高敏感度
            if hasattr(self, "params") and self.params is not None:
                hairnet_conf = self.params.hairnet_detection.confidence_threshold
                # 使用70%的发网检测阈值，但不低于0.2
                hairnet_min_confidence = max(0.2, hairnet_conf * 0.7)

            # 为每个检测到的人体绘制头部框（无论是否有发网检测结果）
            # 创建person_id到发网检测结果的映射
            hairnet_map = {}
            filtered_hairnet_results = [
                result
                for result in hairnet_results
                if result.get("hairnet_confidence", 0.0) >= hairnet_min_confidence
            ]
            for result in filtered_hairnet_results:
                person_id = result.get("person_id")
                if person_id:
                    hairnet_map[person_id] = result

            # 为每个检测到的人体绘制头部框
            for i, detection in enumerate(filtered_person_detections):
                person_bbox = detection.get("bbox", [0, 0, 0, 0])
                if person_bbox == [0, 0, 0, 0]:
                    continue

                x1, y1, x2, y2 = map(int, person_bbox)
                # 计算头部区域（优化：使用35%高度，与YOLOHairnetDetector保持一致）
                person_height = y2 - y1
                person_width = x2 - x1
                head_height = int(person_height * 0.35)  # 从30%增加到35%
                padding_height = int(head_height * 0.2)  # 20%padding
                padding_width = int(person_width * 0.1)  # 10%padding宽度

                head_y1 = max(0, y1 - padding_height)
                head_y2 = min(image.shape[0], y1 + head_height + padding_height)
                head_x1 = max(0, x1 - padding_width)
                head_x2 = min(image.shape[1], x2 + padding_width)

                # 查找对应的发网检测结果
                person_id = i + 1
                hairnet_result = hairnet_map.get(person_id)

                if hairnet_result:
                    # 如果有发网检测结果，优先使用检测结果中的head_bbox（更准确）
                    head_bbox = hairnet_result.get(
                        "head_bbox", [head_x1, head_y1, head_x2, head_y2]
                    )
                    if (
                        head_bbox == [0, 0, 0, 0]
                        or (head_bbox[2] - head_bbox[0] <= 0)
                        or (head_bbox[3] - head_bbox[1] <= 0)
                    ):
                        # 如果head_bbox无效，使用计算的head_bbox
                        head_bbox = [head_x1, head_y1, head_x2, head_y2]
                    else:
                        # 使用检测结果中的head_bbox（来自YOLOHairnetDetector，更准确）
                        head_x1, head_y1, head_x2, head_y2 = map(int, head_bbox)

                    has_hairnet = hairnet_result.get("has_hairnet", False)
                    confidence = hairnet_result.get("hairnet_confidence", 0.0)
                else:
                    # 如果没有发网检测结果，默认显示为无发网（红色）
                    has_hairnet = False
                    confidence = 0.0

                # 绿色=有发网，红色=无发网
                color = (0, 255, 0) if has_hairnet else (0, 0, 255)
                # 绘制头部框（线条粗细3像素）
                cv2.rectangle(
                    annotated, (head_x1, head_y1), (head_x2, head_y2), color, 3
                )

                # 绘制背景框（提高标签可读性）
                label = f"{'有发网' if has_hairnet else '无发网'}"
                if confidence > 0:
                    label += f" {confidence:.2f}"
                (label_width, label_height), baseline = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )
                # 绘制背景
                cv2.rectangle(
                    annotated,
                    (head_x1, head_y1 - label_height - 10),
                    (head_x1 + label_width + 4, head_y1),
                    color,
                    -1,  # 填充
                )

                # 绘制标签（使用更大的字体和更粗的线条）
                cv2.putText(
                    annotated,
                    label,
                    (head_x1 + 2, head_y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,  # 字体大小
                    (255, 255, 255),  # 白色文字，提高对比度
                    2,
                )

            # 过滤低置信度的洗手检测（只显示高置信度的检测）
            filtered_handwash_results = [
                result
                for result in handwash_results
                if result.get("is_handwashing", False)
                and result.get("handwash_confidence", 0.0) >= min_confidence
            ]

            # 绘制洗手检测结果
            for result in filtered_handwash_results:
                person_bbox = result.get("person_bbox", [0, 0, 0, 0])
                x1, y1, x2, y2 = map(int, person_bbox)
                confidence = result.get("handwash_confidence", 0.0)

                # 在人体框上方绘制洗手标签（黄色）
                label = f"洗手中 {confidence:.2f}"
                cv2.putText(
                    annotated,
                    label,
                    (x1, y1 - 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    2,
                )

            # 过滤低置信度的消毒检测（只显示高置信度的检测）
            filtered_sanitize_results = [
                result
                for result in sanitize_results
                if result.get("is_sanitizing", False)
                and result.get("sanitize_confidence", 0.0) >= min_confidence
            ]

            # 绘制消毒检测结果
            for result in filtered_sanitize_results:
                person_bbox = result.get("person_bbox", [0, 0, 0, 0])
                x1, y1, x2, y2 = map(int, person_bbox)
                confidence = result.get("sanitize_confidence", 0.0)

                # 在人体框上方绘制消毒标签（青色）
                label = f"消毒中 {confidence:.2f}"
                cv2.putText(
                    annotated,
                    label,
                    (x1, y1 - 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )

            # 手部可视化：无论是否检测到人体，都尝试绘制手部（便于手部近景视频调试）
            if hand_regions:
                hands_results = hand_regions

                # 绘制手部：优先绘制bbox与来源标签；如有关键点则再绘制骨架
                for hand_result in hands_results:
                    bbox = hand_result.get("bbox", [0, 0, 0, 0])
                    if (
                        bbox == [0, 0, 0, 0]
                        or (bbox[2] - bbox[0] <= 0)
                        or (bbox[3] - bbox[1] <= 0)
                    ):
                        continue

                    hx1, hy1, hx2, hy2 = map(int, bbox)
                    label = hand_result.get("class_name", "hand")
                    hand_result.get("source", "auto")
                    confidence = hand_result.get("confidence", 0.0)

                    # 绘制手部边界框（黄色，线条粗细3像素）
                    cv2.rectangle(annotated, (hx1, hy1), (hx2, hy2), (0, 255, 255), 3)

                    # 绘制标签背景
                    hand_label = f"手部: {label}"
                    if confidence > 0:
                        hand_label += f" {confidence:.2f}"
                    (label_width, label_height), baseline = cv2.getTextSize(
                        hand_label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                    )
                    # 绘制背景
                    cv2.rectangle(
                        annotated,
                        (hx1, hy1 - label_height - 10),
                        (hx1 + label_width + 4, hy1),
                        (0, 255, 255),  # 黄色背景
                        -1,  # 填充
                    )

                    # 绘制标签
                    cv2.putText(
                        annotated,
                        hand_label,
                        (hx1 + 2, hy1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,  # 字体大小
                        (0, 0, 0),  # 黑色文字，提高对比度
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
                                    if finger[j] < len(landmarks) and finger[
                                        j + 1
                                    ] < len(landmarks):
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
