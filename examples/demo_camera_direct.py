import argparse
import json
import logging
import os
import time
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.core.behavior import BehaviorRecognizer

# Import core detection components
from src.core.optimized_detection_pipeline import (
    DetectionResult,
    OptimizedDetectionPipeline,
    VideoStreamOptimizer,
)
from src.core.region import RegionManager, RegionType
from src.core.tracker import MultiObjectTracker  # For direct script tracking
from src.detection.detector import HumanDetector
from src.detection.pose_detector import PoseDetectorFactory
from src.detection.yolo_hairnet_detector import YOLOHairnetDetector

# Import functions from detection_service for drawing and violation capture
from src.services.detection_service import _bbox_overlap, _capture_violation

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Global Pipeline Initialization (similar to app.py) ---
optimized_pipeline: Optional[OptimizedDetectionPipeline] = None
hairnet_pipeline: Optional[YOLOHairnetDetector] = None
region_manager_demo: Optional[RegionManager] = None


def initialize_detection_services_for_demo():
    global optimized_pipeline, hairnet_pipeline, region_manager_demo
    logger.info("Initializing detection services for demo...")
    try:
        # 统一设备选择（mps→cuda→cpu），并打印
        try:
            from src.config.model_config import ModelConfig

            dev = ModelConfig().select_device(requested=None)
        except Exception:
            dev = "auto"
        logger.info(f"设备自动选择结果: {dev}")

        detector = HumanDetector(device=dev)
        behavior_recognizer = BehaviorRecognizer()

        # 根据配置和设备选择姿态检测后端
        from config.unified_params import get_unified_params

        params = get_unified_params()
        pose_backend = params.pose_detection.backend
        if pose_backend == "auto":
            pose_backend = "yolov8" if str(dev).lower() == "cuda" else "mediapipe"

        pose_detector = PoseDetectorFactory.create(
            backend=pose_backend,
            device=params.pose_detection.device
            if params.pose_detection.device != "auto"
            else dev,
        )
        logger.info(f"演示程序 - 姿态检测器后端: {pose_backend}, 设备: {dev}")

        optimized_pipeline = OptimizedDetectionPipeline(
            human_detector=detector,
            hairnet_detector=YOLOHairnetDetector(),
            behavior_recognizer=behavior_recognizer,
            pose_detector=mediapipe_pose_detector,
        )
        hairnet_pipeline = YOLOHairnetDetector(
            device=dev
        )  # Not strictly used by comprehensive, but good to initialize
        logger.info("Detection services initialized for demo.")
        # Load regions for demo (if exists)
        try:
            cfg_path = os.path.join(os.path.dirname(__file__), "config", "regions.json")
            if not os.path.exists(cfg_path):
                # Fallback to absolute workspace layout if running from root
                cfg_path = os.path.join(os.getcwd(), "config", "regions.json")
            rm = RegionManager()
            if rm.load_regions_config(cfg_path):
                region_manager_demo = rm
                logger.info(
                    f"Regions loaded for demo from {cfg_path}, count={len(region_manager_demo.regions)}"
                )
            else:
                logger.warning(
                    "No regions loaded for demo; region-gated logic will be disabled."
                )
        except Exception as e:
            logger.warning(f"Failed to load regions for demo: {e}")
    except Exception as e:
        logger.exception(f"Failed to initialize detection services for demo: {e}")
        optimized_pipeline = None
        hairnet_pipeline = None
        raise


# --- Simple Session-like object for direct script ---
class DemoSession:
    def __init__(
        self,
        track_max_miss: int = 30,
        track_iou_thr: float = 0.2,
        track_dist_thr: float = 200.0,
        track_strategy: str = "hungarian",
        track_iou_weight: float = 0.6,
        track_recycle_ids: bool = False,
        track_force_revival: bool = False,
        track_force_revival_dist: float = 0.0,
        stable_iou_thr: float = 0.2,
        stable_dist_thr: float = 480.0,
        stable_max_ids: int = 2,
    ):
        self.tracker = MultiObjectTracker(
            max_disappeared=track_max_miss,
            iou_threshold=track_iou_thr,
            dist_threshold=track_dist_thr,
            match_strategy=track_strategy,
            iou_weight=track_iou_weight,
            recycle_ids=track_recycle_ids,
            force_revival=track_force_revival,
            force_revival_dist=(
                track_force_revival_dist if track_force_revival_dist > 0 else None
            ),
        )
        self.violation_cooldowns = {}  # For _capture_violation
        # 稳定ID映射（对外显示用）
        self.stable_id_next = 1
        self.track_to_stable = {}  # internal track_id -> stable_id
        self.stable_last = {}  # stable_id -> {"bbox": [x1,y1,x2,y2], "frame": idx}
        self.stable_iou_thr = stable_iou_thr
        self.stable_dist_thr = stable_dist_thr
        self.stable_max_ids = max(1, int(stable_max_ids))
        # 每帧已使用的稳定ID集合，防止同帧内重复分配
        self._used_sids = set()
        self._current_frame_idx = -1

    def begin_frame(self, frame_idx: int):
        # 在处理新帧前重置“已使用稳定ID”集合
        self._used_sids = set()
        self._current_frame_idx = frame_idx

    def _iou(self, a, b):
        if not a or not b:
            return 0.0
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[2], b[2])
        y2 = min(a[3], b[3])
        if x2 <= x1 or y2 <= y1:
            return 0.0
        inter = (x2 - x1) * (y2 - y1)
        area_a = (a[2] - a[0]) * (a[3] - a[1])
        area_b = (b[2] - b[0]) * (b[3] - b[1])
        union = max(1.0, area_a + area_b - inter)
        return inter / union

    def _center_dist(self, a, b):
        ax = (a[0] + a[2]) / 2.0
        ay = (a[1] + a[3]) / 2.0
        bx = (b[0] + b[2]) / 2.0
        by = (b[1] + b[3]) / 2.0
        return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5

    def get_stable_id(
        self,
        track_id: int,
        bbox,
        frame_idx: int,
        iou_thr: float = None,
        dist_thr: float = None,
    ):
        if iou_thr is None:
            iou_thr = self.stable_iou_thr
        if dist_thr is None:
            dist_thr = self.stable_dist_thr
        used_sids = self._used_sids
        # 已存在映射
        if track_id in self.track_to_stable:
            sid = self.track_to_stable[track_id]
            # 更新最近状态
            self.stable_last[sid] = {"bbox": bbox, "frame": frame_idx}
            used_sids.add(sid)
            return sid
        # 试图找到匹配的旧稳定ID（最近若干帧）
        best_sid = None
        best_score = -1.0
        for sid, info in self.stable_last.items():
            # 本帧已被其它目标占用的稳定ID不再复用
            if sid in used_sids:
                continue
            last_bbox = info.get("bbox")
            iou = self._iou(bbox, last_bbox)
            dist = self._center_dist(bbox, last_bbox)
            # 评分：满足IoU或距离阈值即可，优先高IoU，次之近距离
            if iou >= iou_thr or dist <= dist_thr:
                score = iou * 2.0 + max(0.0, 1.0 - dist / max(1.0, dist_thr))
                if score > best_score:
                    best_score = score
                    best_sid = sid
        # 若匹配到未占用的稳定ID，直接使用
        if best_sid is not None:
            self.track_to_stable[track_id] = best_sid
            self.stable_last[best_sid] = {"bbox": bbox, "frame": frame_idx}
            used_sids.add(best_sid)
            return best_sid
        # 未匹配到或均被占用：如未达上限则分配新稳定ID
        if len(self.stable_last) < self.stable_max_ids:
            # 采用自增ID，若当前已占用则继续递增直到找到未占用
            sid = self.stable_id_next
            while sid in self.stable_last or sid in used_sids:
                sid += 1
            self.stable_id_next = sid + 1
            self.track_to_stable[track_id] = sid
            self.stable_last[sid] = {"bbox": bbox, "frame": frame_idx}
            used_sids.add(sid)
            return sid
        # 已达上限：选择距离最近且未在本帧使用的旧ID；若没有，只能复用最相近的一个（极少见）
        candidate_sid = None
        min_dist = 1e18
        for sid, info in self.stable_last.items():
            if sid in used_sids:
                continue
            d = self._center_dist(bbox, info.get("bbox"))
            if d < min_dist:
                min_dist = d
                candidate_sid = sid
        if candidate_sid is None:
            # 所有稳定ID均已在本帧使用，退化为选择整体最近（会与他者重复，理论上仅在>stable_max_ids人数时发生）
            for sid, info in self.stable_last.items():
                d = self._center_dist(bbox, info.get("bbox"))
                if d < min_dist:
                    min_dist = d
                    candidate_sid = sid
        self.track_to_stable[track_id] = candidate_sid
        self.stable_last[candidate_sid] = {"bbox": bbox, "frame": frame_idx}
        used_sids.add(candidate_sid)
        return candidate_sid
        # 分配新的稳定ID
        sid = self.stable_id_next
        self.stable_id_next += 1
        self.track_to_stable[track_id] = sid
        self.stable_last[sid] = {"bbox": bbox, "frame": frame_idx}
        return sid


# --- Main Camera Loop ---
def parse_args():
    parser = argparse.ArgumentParser(
        description="Real-time or video human behavior detection demo"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="0",
        help="Camera index (e.g., '0') or video file path",
    )
    parser.add_argument(
        "--width", type=int, default=424, help="Capture width for camera source"
    )
    parser.add_argument(
        "--height", type=int, default=240, help="Capture height for camera source"
    )
    parser.add_argument(
        "--frame-skip", type=int, default=5, help="Process every Nth frame (optimizer)"
    )
    parser.add_argument(
        "--sim-threshold",
        type=float,
        default=0.995,
        help="Frame similarity threshold for skipping",
    )
    parser.add_argument(
        "--hand-only",
        action="store_true",
        help="Focus on hand behavior: disable hairnet detection",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Stop after processing this many frames (0 = unlimited)",
    )
    parser.add_argument(
        "--exit-on",
        type=str,
        default="none",
        choices=["none", "handwash", "sanitize", "no_hairnet", "no_person"],
        help="Exit when event is observed",
    )
    parser.add_argument(
        "--exit-consecutive",
        type=int,
        default=1,
        help="Consecutive frames required to trigger exit event",
    )
    parser.add_argument(
        "--save-video",
        type=str,
        default="",
        help="Output path to save annotated video (e.g., output/annotated.mp4)",
    )
    parser.add_argument(
        "--save-detail",
        type=str,
        default="",
        help="Path to save per-frame detection details (JSONL)",
    )
    parser.add_argument(
        "--font",
        type=str,
        default="/System/Library/Fonts/PingFang.ttc",
        help="TTF/TTC font path for Chinese OSD text",
    )
    parser.add_argument(
        "--track-iou-thr",
        type=float,
        default=0.2,
        help="Tracker IoU matching threshold (lower=more tolerant)",
    )
    parser.add_argument(
        "--track-dist-thr",
        type=float,
        default=220.0,
        help="Tracker center distance threshold (pixels)",
    )
    parser.add_argument(
        "--track-strategy",
        type=str,
        default="hungarian",
        choices=["hungarian", "greedy"],
        help="Matching strategy",
    )
    parser.add_argument(
        "--track-iou-weight",
        type=float,
        default=0.65,
        help="Fusion weight for IoU vs distance [0..1]",
    )
    parser.add_argument(
        "--track-recycle-ids",
        action="store_true",
        help="Recycle deleted track IDs to reduce ID growth",
    )
    parser.add_argument(
        "--track-force-revival",
        action="store_true",
        help="Force revival of nearby lost IDs with larger distance",
    )
    parser.add_argument(
        "--track-force-revival-dist",
        type=float,
        default=0.0,
        help="Force revival distance in pixels (0=1.5x dist-thr)",
    )
    # Stable ID 控制
    parser.add_argument(
        "--stable-iou-thr",
        type=float,
        default=0.25,
        help="Stable-ID matching IoU threshold",
    )
    parser.add_argument(
        "--stable-dist-thr",
        type=float,
        default=480.0,
        help="Stable-ID matching center distance threshold",
    )
    parser.add_argument(
        "--stable-max-ids",
        type=int,
        default=2,
        help="Max stable IDs allowed in display/export",
    )
    parser.add_argument(
        "--track-max-miss",
        type=int,
        default=30,
        help="Max missed frames before a track is considered lost",
    )
    parser.add_argument(
        "--smooth-window",
        type=int,
        default=5,
        help="Temporal smoothing window (frames) per track_id",
    )
    parser.add_argument(
        "--handwash-min-frames",
        type=int,
        default=3,
        help="Min consecutive frames to confirm handwash per track",
    )
    parser.add_argument(
        "--sanitize-min-frames",
        type=int,
        default=3,
        help="Min consecutive frames to confirm sanitize per track",
    )
    parser.add_argument(
        "--handwash-neg-frames",
        type=int,
        default=5,
        help="Consecutive negative frames to confirm NOT handwashing for violation",
    )
    parser.add_argument(
        "--dump-handseq",
        type=str,
        default="",
        help="Directory to dump hand-sequence npz for training",
    )
    parser.add_argument(
        "--dump-window",
        type=int,
        default=30,
        help="Sequence window length (frames) for dump",
    )
    parser.add_argument(
        "--dump-step",
        type=int,
        default=5,
        help="Dump every N frames per track when window is full",
    )
    # 新增：日志限流与最简OSD
    parser.add_argument(
        "--log-interval",
        type=int,
        default=10,
        help="Print tracking summary every N processed frames (0=disable)",
    )
    parser.add_argument(
        "--osd-minimal",
        action="store_true",
        help="Enable minimal OSD: only bbox and one-line label; no banner",
    )
    parser.add_argument(
        "--draw-regions",
        action="store_true",
        help="Draw configured regions on each frame for verification",
    )
    parser.add_argument(
        "--regions-ref-size",
        type=str,
        default="",
        help="Reference canvas size 'WxH' used when annotating regions (e.g., 1280x720)",
    )
    parser.add_argument(
        "--regions-canvas-size",
        type=str,
        default="",
        help="Frontend canvas size 'WxH' used when annotating (e.g., 1280x720)",
    )
    parser.add_argument(
        "--regions-bg-size",
        type=str,
        default="",
        help="Background image size 'WxH' shown in canvas (e.g., 1920x1080)",
    )
    parser.add_argument(
        "--regions-fit-mode",
        type=str,
        default="contain",
        choices=["contain", "cover", "stretch"],
        help="How background fits in canvas",
    )
    # 新增：洗手融合模式（站立区 AND (ML洗手 OR 水池子区>=N帧)）
    parser.add_argument(
        "--fusion-handwash",
        action="store_true",
        help="Enable fusion: stand area AND (ML handwash OR faucet subregion >= N frames)",
    )
    parser.add_argument(
        "--stand-name",
        type=str,
        default="洗手站立区域",
        help="Name of standing area region for handwash gating",
    )
    parser.add_argument(
        "--faucet-name",
        type=str,
        default="洗手水池",
        help="Name of faucet sub-region for handwash fusion",
    )
    parser.add_argument(
        "--faucet-min-frames",
        type=int,
        default=3,
        help="Min consecutive frames in faucet sub-region to count as washing",
    )
    parser.add_argument(
        "--log-fusion-details",
        action="store_true",
        help="Log per-frame fusion details for handwash decision",
    )
    parser.add_argument(
        "--osd-debug-hand",
        action="store_true",
        help="Always draw hand boxes/landmarks and ML score for debugging",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    initialize_detection_services_for_demo()

    if optimized_pipeline is None:
        logger.error("Detection pipeline not initialized. Exiting.")
        return

    # Open source: camera index or video file
    source_str = args.source
    cap = None
    if source_str.isdigit():
        cam_index = int(source_str)
        cap = cv2.VideoCapture(cam_index, cv2.CAP_AVFOUNDATION)
        if not cap or not cap.isOpened():
            cap = cv2.VideoCapture(cam_index)
        if not cap or not cap.isOpened():
            logger.error("Error: Could not open webcam.")
            return
        # Set lower resolution for better throughput unless user overrides
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    else:
        if not os.path.exists(source_str):
            logger.error(f"Error: Video file not found: {source_str}")
            return
        cap = cv2.VideoCapture(source_str)
        if not cap or not cap.isOpened():
            logger.error(f"Error: Could not open video file: {source_str}")
            return

    logger.info("Webcam opened successfully. Press 'q' to quit.")

    # Prepare outputs
    writer = None
    detail_reports = [] if args.save_detail else None
    if args.save_video:
        # Ensure directory exists
        out_path = args.save_video
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        # Determine fps from source
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 1:
            fps = 20.0
        # Determine frame size lazily after first frame
        writer_info = {"path": out_path, "fps": fps, "size": None}

    demo_session = DemoSession(
        track_max_miss=args.track_max_miss,
        track_iou_thr=args.track_iou_thr,
        track_dist_thr=args.track_dist_thr,
        track_strategy=args.track_strategy,
        track_iou_weight=args.track_iou_weight,
        track_recycle_ids=args.track_recycle_ids,
        track_force_revival=args.track_force_revival,
        track_force_revival_dist=args.track_force_revival_dist,
        stable_iou_thr=args.stable_iou_thr,
        stable_dist_thr=args.stable_dist_thr,
        stable_max_ids=args.stable_max_ids,
    )  # Create a session for this demo
    optimizer = None
    if not args.hand_only:
        optimizer = VideoStreamOptimizer(
            optimized_pipeline,
            frame_skip=args.frame_skip,
            similarity_threshold=args.sim_threshold,
        )
    last_annotated = None
    last_result = None
    # Per-track temporal states
    track_states = {}
    # Per-track compliance state machine (lite)
    compliance_state = (
        {}
    )  # track_id -> {hairnet_ok:bool, handwash_ok:bool, sanitize_ok:bool}
    # Per-track sequence buffers for ML data dump
    track_seq_buffers = {}

    def _normalize_landmarks_to_person(lmks, person_bbox, image_shape):
        x1, y1, x2, y2 = map(int, person_bbox)
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        norm = []
        for lm in lmks:
            x = float(lm.get("x", 0))
            y = float(lm.get("y", 0))
            # If landmarks are absolute pixels, keep as is; otherwise, if 0..1, scale by image size
            if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                h, w = image_shape[:2]
                x *= w
                y *= h
            nx = (x - x1) / width
            ny = (y - y1) / height
            # clamp
            nx = 0.0 if nx < 0 else (1.0 if nx > 1.0 else nx)
            ny = 0.0 if ny < 0 else (1.0 if ny > 1.0 else ny)
            norm.extend([nx, ny])
        return norm

    def _extract_two_hands_vector(hand_regions, person_bbox, image_shape):
        # pick up to 2 hands by confidence
        hands_sorted = sorted(
            hand_regions, key=lambda h: float(h.get("confidence", 0.0)), reverse=True
        )
        vec = []
        hands_taken = 0
        for hreg in hands_sorted:
            if hands_taken >= 2:
                break
            lmks = hreg.get("landmarks", [])
            if not lmks:
                # fill zeros for missing landmarks
                vec.extend([0.0] * (21 * 2))
            else:
                # ensure length 21
                lmks = lmks[:21] + [{}] * max(0, 21 - len(lmks))
                vec.extend(
                    _normalize_landmarks_to_person(lmks, person_bbox, image_shape)
                )
            hands_taken += 1
        # if less than 2 hands, pad
        while hands_taken < 2:
            vec.extend([0.0] * (21 * 2))
            hands_taken += 1
        return vec

    try:
        consecutive_failures = 0
        max_failures = 5
        frame_read_count = 0
        event_consecutive = 0
        no_person_streak = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                consecutive_failures += 1
                logger.warning(f"Failed to grab frame (#{consecutive_failures}).")
                if consecutive_failures >= max_failures:
                    logger.error("Too many consecutive frame grab failures. Exiting.")
                    break
                time.sleep(0.1)
                continue
            else:
                consecutive_failures = 0
                frame_read_count += 1

            # Stop if frame limit reached
            if args.max_frames > 0 and frame_read_count >= args.max_frames:
                logger.info(f"Max frames reached ({args.max_frames}). Exiting.")
                break

            # --- 在第一帧按视频尺寸缩放区域，并在每帧绘制区域 ---
            if region_manager_demo is not None:
                try:
                    h0, w0 = frame.shape[:2]
                    # 仅首帧缩放一次
                    if frame_read_count == 1:
                        canv = (args.regions_canvas_size or "").lower().strip()
                        bg = (args.regions_bg_size or "").lower().strip()
                        if "x" in canv and "x" in bg:
                            try:
                                cw, ch = map(int, canv.split("x", 1))
                                bw, bh = map(int, bg.split("x", 1))
                                if cw > 0 and ch > 0 and bw > 0 and bh > 0:
                                    region_manager_demo.scale_from_canvas_and_bg(
                                        cw,
                                        ch,
                                        bw,
                                        bh,
                                        w0,
                                        h0,
                                        fit_mode=args.regions_fit_mode,
                                    )
                                else:
                                    region_manager_demo.scale_to_frame_if_needed(w0, h0)
                            except Exception:
                                region_manager_demo.scale_to_frame_if_needed(w0, h0)
                        else:
                            ref = (args.regions_ref_size or "").lower().strip()
                            if "x" in ref:
                                try:
                                    rw, rh = ref.split("x", 1)
                                    rw = int(rw)
                                    rh = int(rh)
                                    if rw > 0 and rh > 0:
                                        region_manager_demo.scale_from_reference(
                                            rw, rh, w0, h0
                                        )
                                    else:
                                        region_manager_demo.scale_to_frame_if_needed(
                                            w0, h0
                                        )
                                except Exception:
                                    region_manager_demo.scale_to_frame_if_needed(w0, h0)
                            else:
                                region_manager_demo.scale_to_frame_if_needed(w0, h0)
                except Exception:
                    pass

            # --- Unified detection flow (optimizer or direct with flags) ---
            result = None
            if args.hand_only:
                # 仅洗手：禁用发网与消毒
                result = optimized_pipeline.detect_comprehensive(
                    frame,
                    enable_hairnet=False,
                    enable_handwash=True,
                    enable_sanitize=False,
                )
            else:
                result = (
                    optimizer.process_frame(frame)
                    if optimizer is not None
                    else optimized_pipeline.detect_comprehensive(frame)
                )

            if result is not None:
                # Tracker based on person detections
                person_detections = result.person_detections or []
                # 更新无人计数（仅在开启 no_person 退出条件时生效）
                if args.exit_on == "no_person":
                    if len(person_detections) == 0:
                        no_person_streak += 1
                    else:
                        no_person_streak = 0
            else:
                # 本帧无新结果，回放上一帧标注并进入下一循环
                if last_annotated is not None:
                    cv2.imshow("Real-time Detection (Direct Camera)", last_annotated)
                else:
                    cv2.imshow("Real-time Detection (Direct Camera)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    logger.info("Exiting application.")
                    break
                continue
            tracker_input = [
                {"bbox": p.get("bbox"), "confidence": p.get("confidence")}
                for p in person_detections
            ]
            tracked_objects = demo_session.tracker.update(tracker_input)

            # 日志输出：当前帧的稳定编号列表（隐藏内部ID）
            try:
                if args.log_interval and (
                    frame_read_count % max(1, args.log_interval) == 0
                ):

                    def _sid_str(tobj):
                        sid = demo_session.get_stable_id(
                            tobj["track_id"],
                            tobj["bbox"],
                            frame_read_count,
                            iou_thr=max(0.25, args.stable_iou_thr),
                            dist_thr=max(args.stable_dist_thr, 320.0),
                        )
                        return f"编号{sid}@{tuple(map(int, tobj['bbox']))}"

                    ids_text = ", ".join([_sid_str(t) for t in tracked_objects])
                    logger.info(f"跟踪人数={len(tracked_objects)}，稳定编号: {ids_text}")
            except Exception:
                pass

                # Propagate track_id to matched detections (optional)
            tracked_person_detections = []
            for tobj in tracked_objects:
                for pdet in person_detections:
                    if _bbox_overlap(tobj["bbox"], pdet["bbox"], threshold=0.8):
                        pdet["track_id"] = tobj["track_id"]
                        tracked_person_detections.append(pdet)
                        break

                hairnet_results = result.hairnet_results
                handwash_results = result.handwash_results
                sanitize_results = result.sanitize_results

                # Build quick lookup by overlapping person_bbox
                def _match_flag(results_list, person_bbox, key):
                    for r in results_list:
                        if _bbox_overlap(person_bbox, r.get("person_bbox", [])):
                            return bool(r.get(key, False))
                    return False

                def _find_result(results_list, person_bbox):
                    for r in results_list:
                        if _bbox_overlap(person_bbox, r.get("person_bbox", [])):
                            return r
                    return None

                # --- Annotation and Display ---
                # 使用原始帧作为底图，避免底层管道中的英文注释
                annotated = frame.copy()
                # 绘制区域轮廓（便于核对位置/大小）
                if region_manager_demo is not None and args.draw_regions:
                    try:
                        for r in region_manager_demo.regions.values():
                            poly = [(int(x), int(y)) for (x, y) in r.polygon]
                            if len(poly) >= 2:
                                cv2.polylines(
                                    annotated,
                                    [np.array(poly, dtype=np.int32)],
                                    isClosed=True,
                                    color=(255, 0, 0),
                                    thickness=2,
                                )
                                # 在区域中心写名字
                                cx, cy = map(int, r.get_center())
                                cx = max(0, min(cx, annotated.shape[1] - 1))
                                cy = max(0, min(cy, annotated.shape[0] - 1))
                                cv2.putText(
                                    annotated,
                                    (r.name or r.region_type.value),
                                    (cx, cy),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.6,
                                    (255, 0, 0),
                                    2,
                                )
                    except Exception:
                        pass
                frame_violations = []  # Collect OSD messages for this frame
                frame_report = None
                if detail_reports is not None:
                    frame_report = {
                        "frame_idx": frame_read_count,
                        "objects": [],
                        "violations": [],
                    }

                # Helper: batch Chinese text draw using PIL once per frame
                _osd_queue = []  # list of (text, (x,y), font_size, color)

                def _queue_text(text, org, font_size=16, color=(255, 255, 255)):
                    _osd_queue.append(
                        (
                            str(text),
                            (int(org[0]), int(org[1])),
                            int(font_size),
                            (int(color[0]), int(color[1]), int(color[2])),
                        )
                    )

                def _flush_text(img):
                    if not _osd_queue:
                        return img
                    try:
                        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                        draw = ImageDraw.Draw(pil_img)
                        try:
                            font_path = args.font
                            # 简化：不同字号仍复用同一路径，实际可按需缓存字体对象
                        except Exception:
                            font_path = None
                        for text, org, fsize, bgr in _osd_queue:
                            try:
                                font = (
                                    ImageFont.truetype(font_path, fsize)
                                    if font_path
                                    else ImageFont.load_default()
                                )
                            except Exception:
                                font = ImageFont.load_default()
                            draw.text(
                                org, text, font=font, fill=(bgr[2], bgr[1], bgr[0])
                            )
                        _osd_queue.clear()
                        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                    except Exception:
                        # Fallback: 用简化ASCII逐条画（不支持中文会乱码）
                        for text, org, fsize, bgr in _osd_queue:
                            cv2.putText(
                                img,
                                text,
                                org,
                                cv2.FONT_HERSHEY_SIMPLEX,
                                max(0.5, fsize / 24.0),
                                bgr,
                                2,
                            )
                        _osd_queue.clear()
                        return img

                for tobj in tracked_objects:
                    bbox = tobj["bbox"]
                    track_id = tobj["track_id"]
                    # 计算稳定ID（对外显示）
                    stable_id = demo_session.get_stable_id(
                        track_id,
                        bbox,
                        frame_read_count,
                        iou_thr=max(0.25, args.track_iou_thr),
                        dist_thr=max(args.track_dist_thr, 320.0),
                    )
                    x1, y1, x2, y2 = map(int, bbox)
                    # Update region occupancy for this track
                    inside_entrance = False
                    inside_handwash = False
                    inside_sanitize = False
                    inside_work_area = False
                    inside_faucet = False
                    if region_manager_demo is not None:
                        region_ids = region_manager_demo.update_track_regions(
                            track_id, bbox
                        )
                        for rid in region_ids:
                            r = region_manager_demo.regions.get(rid)
                            if not r:
                                continue
                            if r.region_type == RegionType.ENTRANCE:
                                inside_entrance = True
                            elif r.region_type == RegionType.HANDWASH:
                                inside_handwash = True
                            elif r.region_type == RegionType.SANITIZE:
                                inside_sanitize = True
                            elif r.region_type == RegionType.WORK_AREA:
                                inside_work_area = True
                            # 名称匹配（用于子区域/站立区未设类型时）
                            try:
                                rname = (r.name or "").strip()
                                if rname == args.faucet_name:
                                    inside_faucet = True
                                if rname == args.stand_name:
                                    inside_handwash = True
                            except Exception:
                                pass
                    # Temporal smoothing per track
                    st = track_states.setdefault(
                        track_id,
                        {
                            "hw_cnt": 0,
                            "sz_cnt": 0,
                            "hw_false": 0,
                            "sz_false": 0,
                            "hw_neg_cnt": 0,
                            "last_ts": time.time(),
                            "faucet_cnt": 0,
                        },
                    )
                    is_hw_raw = _match_flag(handwash_results, bbox, "is_handwashing")
                    is_sz_raw = _match_flag(sanitize_results, bbox, "is_sanitizing")
                    # Gate behaviors by regions / 融合逻辑
                    # 仅消毒在 SANITIZE 区域计数
                    is_sz = is_sz_raw and (
                        inside_sanitize if region_manager_demo is not None else True
                    )
                    # 水池子区连续帧计数
                    if inside_faucet:
                        st["faucet_cnt"] = min(args.smooth_window, st["faucet_cnt"] + 1)
                    else:
                        st["faucet_cnt"] = max(0, st["faucet_cnt"] - 1)
                    # 洗手融合：站立区 AND (ML洗手 OR 水池>=N帧)
                    if args.fusion_handwash:
                        is_hw_fused = (
                            inside_handwash if region_manager_demo is not None else True
                        ) and (
                            bool(is_hw_raw)
                            or (
                                st.get("faucet_cnt", 0)
                                >= max(1, args.faucet_min_frames)
                            )
                        )
                        is_hw = is_hw_fused
                    else:
                        # 仅区域门控：HANDWASH 区域内且 ML 洗手为真
                        is_hw = is_hw_raw and (
                            inside_handwash if region_manager_demo is not None else True
                        )
                    # Update counters (bounded by smooth window)
                    st["hw_cnt"] = (
                        min(args.smooth_window, st["hw_cnt"] + 1)
                        if is_hw
                        else max(0, st["hw_cnt"] - 1)
                    )
                    st["sz_cnt"] = (
                        min(args.smooth_window, st["sz_cnt"] + 1)
                        if is_sz
                        else max(0, st["sz_cnt"] - 1)
                    )
                    # Only accumulate negative count when inside the corresponding region
                    if region_manager_demo is None or inside_handwash:
                        st["hw_neg_cnt"] = (
                            min(args.smooth_window, st["hw_neg_cnt"] + 1)
                            if (not is_hw)
                            else max(0, st["hw_neg_cnt"] - 1)
                        )
                    hw_confirm = st["hw_cnt"] >= args.handwash_min_frames
                    sz_confirm = st["sz_cnt"] >= args.sanitize_min_frames
                    # 详细日志：帧号 + 融合信号
                    if args.log_fusion_details:
                        try:
                            logger.info(
                                f"帧 {frame_read_count} 编号{stable_id} 融合判定: 站立区={inside_handwash}, 水池={inside_faucet}, "
                                f"水池计数={st.get('faucet_cnt', 0)}, ML洗手={bool(is_hw_raw)}, 融合结果={bool(is_hw)}, "
                                f"hw_cnt={st.get('hw_cnt', 0)}, 确认={hw_confirm}"
                            )
                        except Exception:
                            pass
                    # 根据洗手状态绘制不同颜色的人员框
                    box_color = (
                        (0, 215, 255) if hw_confirm else (0, 255, 0)
                    )  # 洗手=黄青色，否则绿色
                    thickness = 3 if hw_confirm else 2
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, thickness)
                    # 手部可视化与ML置信度调试
                    try:
                        if args.osd_debug_hand or hw_confirm:
                            hand_regions = (
                                optimized_pipeline.get_hand_regions_for_person(
                                    frame, bbox
                                )
                            )
                            # 绘制人体中线
                            cx_mid = int((x1 + x2) / 2)
                            cv2.line(
                                annotated,
                                (cx_mid, y1),
                                (cx_mid, y2),
                                (200, 200, 200),
                                1,
                            )
                            # 仅取前两只手用于可视化
                            centers = []
                            for hreg in (hand_regions or [])[:2]:
                                hb = hreg.get("bbox", [0, 0, 0, 0])
                                hx1, hy1, hx2, hy2 = [int(v) for v in hb]
                                cv2.rectangle(
                                    annotated, (hx1, hy1), (hx2, hy2), (255, 255, 0), 2
                                )
                                # 手中心点
                                hc = (int((hx1 + hx2) / 2), int((hy1 + hy2) / 2))
                                centers.append(hc)
                                cv2.circle(annotated, hc, 3, (255, 255, 0), -1)
                                # 关键点
                                lmks = hreg.get("landmarks", [])
                                for lm in lmks:
                                    px = lm.get("x", -1)
                                    py = lm.get("y", -1)
                                    if px is None or py is None:
                                        continue
                                    # 兼容：若为归一化(0..1)，需要乘以图像宽高；若已是像素，直接使用
                                    if (
                                        0.0 <= float(px) <= 1.0
                                        and 0.0 <= float(py) <= 1.0
                                    ):
                                        lx = int(float(px) * annotated.shape[1])
                                        ly = int(float(py) * annotated.shape[0])
                                    else:
                                        lx = int(px)
                                        ly = int(py)
                                    if (
                                        0 <= lx < annotated.shape[1]
                                        and 0 <= ly < annotated.shape[0]
                                    ):
                                        cv2.circle(
                                            annotated, (lx, ly), 2, (0, 215, 255), -1
                                        )
                            # 计算是否“交叉”（左右手相对人体中线的符号是否异常）
                            crossing = None
                            if len(centers) == 2:
                                dx0 = centers[0][0] - cx_mid
                                dx1 = centers[1][0] - cx_mid
                                # 一左一右为正常；若同侧或频繁换侧可视为可能“交叉/互换”
                                crossing = dx0 * dx1 > 0
                            # ML置信度
                            hw_res = _find_result(handwash_results, bbox)
                            p_ml = 0.0
                            if hw_res is not None:
                                p_ml = float(hw_res.get("handwash_confidence", 0.0))
                            # 文本调试信息
                            dbg_text = f"p_ml={p_ml:.3f} 交叉={'是' if crossing else '否' if crossing is not None else '未知'} 站立区={inside_handwash} 水池={inside_faucet} 计数={st.get('faucet_cnt',0)} 融合={bool(is_hw)}"
                            _queue_text(
                                dbg_text,
                                (x1, min(y2 + 18, annotated.shape[0] - 5)),
                                font_size=15,
                                color=(255, 255, 0),
                            )
                    except Exception:
                        pass
                    # Update compliance state (sequence)
                    comp = compliance_state.setdefault(
                        track_id,
                        {
                            "hairnet_ok": False,
                            "handwash_ok": False,
                            "sanitize_ok": False,
                        },
                    )
                    # Entrance hairnet check (only when inside entrance region and hairnet results available)
                    has_hairnet = None
                    if not args.hand_only:
                        for h_res in hairnet_results:
                            if _bbox_overlap(bbox, h_res.get("person_bbox", [])):
                                has_hairnet = bool(h_res.get("has_hairnet", False))
                                break
                    if not args.hand_only and inside_entrance and has_hairnet is True:
                        comp["hairnet_ok"] = True
                    # Handwash completion only valid if hairnet already OK (sequence)
                    if hw_confirm and (comp["hairnet_ok"] or args.hand_only):
                        comp["handwash_ok"] = True
                    # Sanitize completion only valid if handwash already OK
                    if sz_confirm and comp["handwash_ok"]:
                        comp["sanitize_ok"] = True
                    # Determine next required step
                    next_step = None
                    if not comp["hairnet_ok"]:
                        next_step = "hairnet"
                    elif not comp["handwash_ok"]:
                        next_step = "handwash"
                    elif not comp["sanitize_ok"]:
                        next_step = "sanitize"
                    else:
                        next_step = "enter"
                    label = f"编号:{stable_id}"
                    if hw_confirm:
                        label += " | 洗手"
                    if sz_confirm:
                        label += " | 消毒"
                    # Add sequence status（中文）- hand_only 下不显示流程
                    if not args.hand_only:
                        seq_txt_cn = []
                        if comp.get("hairnet_ok"):
                            seq_txt_cn.append("发网")
                        if comp.get("handwash_ok"):
                            seq_txt_cn.append("洗手")
                        if comp.get("sanitize_ok"):
                            seq_txt_cn.append("消毒")
                        if seq_txt_cn:
                            label += f" | 流程:{'→'.join(seq_txt_cn)}"
                    if args.osd_minimal:
                        # 仅一行标签
                        _queue_text(
                            label,
                            (x1, max(12, y1 - 12)),
                            font_size=16,
                            color=(0, 255, 0),
                        )
                    else:
                        _queue_text(
                            label,
                            (x1, max(12, y1 - 12)),
                            font_size=16,
                            color=(0, 255, 0),
                        )
                    # Draw NEXT step hint
                    if not args.osd_minimal and not args.hand_only:
                        if next_step and next_step != "enter":
                            next_map = {
                                "hairnet": "发网",
                                "handwash": "洗手",
                                "sanitize": "消毒",
                            }
                            hint = f"下一步: {next_map.get(next_step, next_step)}"
                            _queue_text(
                                hint,
                                (x1, min(y2 + 20, annotated.shape[0] - 5)),
                                font_size=17,
                                color=(0, 215, 255),
                            )
                        elif next_step == "enter":
                            _queue_text(
                                "流程完成",
                                (x1, min(y2 + 20, annotated.shape[0] - 5)),
                                font_size=17,
                                color=(0, 255, 0),
                            )

                    # Append to frame report（含下一步）
                    if frame_report is not None:
                        frame_report["objects"].append(
                            {
                                "track_id": int(track_id),
                                "stable_id": int(stable_id),
                                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                                "regions": {
                                    "entrance": bool(inside_entrance),
                                    "handwash": bool(inside_handwash),
                                    "sanitize": bool(inside_sanitize),
                                    "faucet": bool(inside_faucet),
                                },
                                "hairnet": None
                                if has_hairnet is None
                                else bool(has_hairnet),
                                "handwash": {
                                    "raw": bool(is_hw_raw),
                                    "smoothed": bool(hw_confirm),
                                    "count": int(st["hw_cnt"]),
                                },
                                "sanitize": {
                                    "raw": bool(is_sz_raw),
                                    "smoothed": bool(sz_confirm),
                                    "count": int(st["sz_cnt"]),
                                },
                                "sequence": {
                                    "hairnet_ok": bool(comp.get("hairnet_ok", False)),
                                    "handwash_ok": bool(comp.get("handwash_ok", False)),
                                    "sanitize_ok": bool(comp.get("sanitize_ok", False)),
                                },
                                "next_step": next_step,
                            }
                        )

                    # --- Dump hand sequence window for ML training ---
                    if args.dump_handseq:
                        try:
                            hand_regions = (
                                optimized_pipeline.get_hand_regions_for_person(
                                    frame, bbox
                                )
                            )
                            vec = _extract_two_hands_vector(
                                hand_regions, bbox, frame.shape
                            )
                            buf = track_seq_buffers.setdefault(track_id, [])
                            buf.append(
                                {
                                    "feat": vec,
                                    "label": 1 if hw_confirm else 0,
                                }
                            )
                            if len(buf) > args.dump_window:
                                buf.pop(0)
                            if len(buf) == args.dump_window and (
                                frame_read_count % args.dump_step == 0
                            ):
                                # save npz: features (window, feat_dim), labels (window,)
                                feats = np.array(
                                    [b["feat"] for b in buf], dtype=np.float32
                                )
                                labels = np.array(
                                    [b["label"] for b in buf], dtype=np.int8
                                )
                                os.makedirs(args.dump_handseq, exist_ok=True)
                                out_name = f"track{track_id}_f{frame_read_count}.npz"
                                out_path = os.path.join(args.dump_handseq, out_name)
                                np.savez_compressed(
                                    out_path,
                                    feats=feats,
                                    labels=labels,
                                    track_id=track_id,
                                )
                        except Exception as _:
                            pass

                    # OSD violations (simple):
                    # 1) No hairnet (only when inside entrance region)
                    if not args.hand_only and inside_entrance:
                        for h_res in hairnet_results:
                            if _bbox_overlap(
                                bbox, h_res.get("person_bbox", [])
                            ) and not h_res.get("has_hairnet", True):
                                frame_violations.append(f"编号 {stable_id}: 未佩戴发网")
                                cv2.rectangle(
                                    annotated, (x1, y1), (x2, y2), (0, 0, 255), 2
                                )
                                break
                    # 2) Not handwashing (negative streak)
                    if (region_manager_demo is None or inside_handwash) and st.get(
                        "hw_neg_cnt", 0
                    ) >= max(1, args.handwash_neg_frames):
                        frame_violations.append(f"编号 {stable_id}: 未洗手")
                        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    # 3) Sequence violations based on regions
                    if inside_handwash and not (comp["hairnet_ok"] or args.hand_only):
                        frame_violations.append(f"编号 {stable_id}: 未戴发网进入洗手区")
                    if inside_sanitize and not comp["handwash_ok"]:
                        frame_violations.append(f"编号 {stable_id}: 未洗手进入消毒区")
                    if inside_work_area and not (
                        comp["hairnet_ok"]
                        and comp["handwash_ok"]
                        and comp["sanitize_ok"]
                    ):
                        frame_violations.append(f"编号 {stable_id}: 未完成流程进入工作区")

                # Draw OSD banner (top-left) if any
                if frame_violations and not args.osd_minimal:
                    # 简化顶部横幅：改用排队绘制而不做半透明覆盖
                    y = 18
                    for msg in frame_violations:
                        _queue_text(msg, (10, y), font_size=16, color=(255, 255, 255))
                        y += 18
                if frame_report is not None:
                    frame_report["violations"] = list(frame_violations)
                    detail_reports.append(frame_report)

                # 一次性刷出所有文本
                annotated = _flush_text(annotated)
                last_annotated = annotated
                last_result = result
                cv2.imshow("Real-time Detection (Direct Camera)", annotated)

                # Write annotated frame if requested
                if args.save_video:
                    if writer is None:
                        h, w = annotated.shape[:2]
                        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                        writer = cv2.VideoWriter(
                            writer_info["path"], fourcc, writer_info["fps"], (w, h)
                        )
                        writer_info["size"] = (w, h)
                    writer.write(annotated)

                # Exit trigger based on event
                if args.exit_on != "none":
                    event_present = False
                    if args.exit_on == "handwash":
                        # Use smoothed decision
                        event_present = any(
                            track_states.get(t["track_id"], {}).get("hw_cnt", 0)
                            >= args.handwash_min_frames
                            for t in tracked_objects
                        )
                    elif args.exit_on == "sanitize":
                        event_present = any(
                            track_states.get(t["track_id"], {}).get("sz_cnt", 0)
                            >= args.sanitize_min_frames
                            for t in tracked_objects
                        )
                    elif args.exit_on == "no_hairnet":
                        if not args.hand_only:
                            event_present = any(
                                not h.get("has_hairnet", True) for h in hairnet_results
                            )
                    elif args.exit_on == "no_person":
                        # 连续若干帧无人：采用 smooth-window 作为容忍帧数
                        event_present = no_person_streak >= max(3, args.smooth_window)

                    if event_present:
                        event_consecutive += 1
                    else:
                        event_consecutive = 0

                    if event_consecutive >= max(1, args.exit_consecutive):
                        logger.info(
                            f"Exit event '{args.exit_on}' observed for {event_consecutive} consecutive processed frames. Exiting."
                        )
                        break

            # --- Violation Capture Logic (only when new detection result exists) ---
            if result is not None:
                for tobj in tracked_objects:
                    track_id = tobj["track_id"]
                    person_bbox = tobj["bbox"]

                    # Hairnet violation
                    if not args.hand_only:
                        for h_res in hairnet_results:
                            if _bbox_overlap(
                                person_bbox, h_res.get("person_bbox", [])
                            ) and not h_res.get("has_hairnet"):
                                _capture_violation(
                                    demo_session,
                                    frame,
                                    track_id,
                                    "no_hairnet",
                                    person_bbox,
                                )
                                break  # Only capture once per person per frame for this violation type

                    # Handwashing violation (absence of behavior)
                    st = track_states.get(track_id, {})
                    if st.get("hw_neg_cnt", 0) >= max(1, args.handwash_neg_frames):
                        _capture_violation(
                            demo_session,
                            frame,
                            track_id,
                            "not_handwashing",
                            person_bbox,
                        )

            # --- Exit Condition ---
            if cv2.waitKey(1) & 0xFF == ord("q"):
                logger.info("Exiting application.")
                break

    except Exception as e:
        logger.exception(f"An error occurred during real-time detection: {e}")
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()
        # Save detail reports if requested
        try:
            if detail_reports is not None and len(detail_reports) > 0:
                os.makedirs(os.path.dirname(args.save_detail) or ".", exist_ok=True)
                with open(args.save_detail, "w", encoding="utf-8") as f:
                    for rec in detail_reports:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                logger.info(
                    f"Detailed detection report saved to {args.save_detail} ({len(detail_reports)} frames)"
                )
        except Exception as _:
            logger.warning("Failed to save detailed detection report")
        logger.info("Webcam released and windows destroyed.")


if __name__ == "__main__":
    main()
