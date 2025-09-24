import base64
import logging
import os
import time
from typing import Optional

import cv2
import numpy as np

from src.core.optimized_detection_pipeline import (
    DetectionResult,
    OptimizedDetectionPipeline,
)
from src.core.tracker import MultiObjectTracker
from src.detection.pose_detector import PoseDetectorFactory
from src.detection.yolo_hairnet_detector import YOLOHairnetDetector

logger = logging.getLogger(__name__)

# Global instances, initialized at startup
optimized_pipeline: Optional[OptimizedDetectionPipeline] = None
hairnet_pipeline: Optional[YOLOHairnetDetector] = None


def comprehensive_detection_logic(
    contents: bytes,
    filename: str,
    optimized_pipeline: Optional[OptimizedDetectionPipeline],
    hairnet_pipeline: Optional[YOLOHairnetDetector],
    record_process: bool = False,
) -> dict:
    import tempfile
    from pathlib import Path

    file_ext = Path(filename).suffix.lower()
    video_extensions = {".mp4", ".avi", ".mov"}
    image_extensions = {".jpg", ".jpeg", ".png"}

    image = None
    if file_ext in video_extensions:
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
            temp_file.write(contents)
            temp_video_path = temp_file.name
        try:
            if record_process and optimized_pipeline:
                return _process_video_with_recording(
                    temp_video_path, filename, optimized_pipeline
                )
            else:
                cap = cv2.VideoCapture(temp_video_path)
                ret, frame = cap.read()
                cap.release()
                if not ret or frame is None:
                    raise ValueError("Could not read frame from video")
                image = frame
        finally:
            os.unlink(temp_video_path)
    elif file_ext in image_extensions:
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Could not decode image")
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")

    if image is None:
        raise ValueError("Could not get a valid image to process")

    if not optimized_pipeline:
        raise RuntimeError("Detection service not initialized")

    result = optimized_pipeline.detect_comprehensive(image)

    total_persons = len(result.person_detections)
    statistics = {
        "persons_with_hairnet": len(
            [h for h in result.hairnet_results if h.get("has_hairnet", False)]
        ),
        "persons_handwashing": len(
            [h for h in result.handwash_results if h.get("is_handwashing", False)]
        ),
        "persons_sanitizing": len(
            [s for s in result.sanitize_results if s.get("is_sanitizing", False)]
        ),
    }
    detections = []
    for det in result.person_detections:
        detections.append(
            {
                "class": "person",
                "confidence": det.get("confidence", 0.0),
                "bbox": det.get("bbox"),
            }
        )

    annotated_image_b64 = None
    if result.annotated_image is not None:
        _, buffer = cv2.imencode(".jpg", result.annotated_image)
        annotated_image_b64 = base64.b64encode(buffer.tobytes()).decode("utf-8")

    return {
        "total_persons": total_persons,
        "statistics": statistics,
        "detections": detections,
        "annotated_image": annotated_image_b64,
        "processing_times": result.processing_times,
    }


def initialize_detection_services():
    global optimized_pipeline, hairnet_pipeline
    logger.info("Initializing detection services...")
    try:
        from src.core.behavior import BehaviorRecognizer
        from src.detection.detector import HumanDetector

        detector = HumanDetector()
        behavior_recognizer = BehaviorRecognizer()

        # 根据配置和设备选择姿态检测后端
        from config.unified_params import get_unified_params
        from src.config.model_config import ModelConfig

        params = get_unified_params()
        device = ModelConfig().select_device(requested=None)

        pose_backend = params.pose_detection.backend
        if pose_backend == "auto":
            pose_backend = "yolov8" if str(device).lower() == "cuda" else "mediapipe"

        pose_detector = PoseDetectorFactory.create(
            backend=pose_backend,
            device=params.pose_detection.device
            if params.pose_detection.device != "auto"
            else device,
        )
        logger.info(f"API服务 - 姿态检测器后端: {pose_backend}, 设备: {device}")

        optimized_pipeline = OptimizedDetectionPipeline(
            human_detector=detector,
            hairnet_detector=YOLOHairnetDetector(),
            behavior_recognizer=behavior_recognizer,
            pose_detector=pose_detector,
        )
        hairnet_pipeline = YOLOHairnetDetector()
        logger.info("Detection services initialized.")
    except Exception as e:
        logger.exception(f"Failed to initialize detection services: {e}")
        optimized_pipeline = None
        hairnet_pipeline = None
        raise


def _process_video_with_recording(
    video_path: str, filename: str, optimized_pipeline: OptimizedDetectionPipeline
) -> dict:
    from pathlib import Path

    logger.info(f"Processing video: {filename}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Cannot open video file")

    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_dir = "./output/processed_videos"
    os.makedirs(output_dir, exist_ok=True)
    base_name = Path(filename).stem
    output_filename = f"{base_name}_processed_{int(time.time())}.mp4"
    output_path = os.path.join(output_dir, output_filename)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    tracker = MultiObjectTracker(max_disappeared=5, iou_threshold=0.5)
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        if frame_count % 5 == 0:
            result = optimized_pipeline.detect_comprehensive(frame)
            detections = [
                {"bbox": p["bbox"], "confidence": p["confidence"]}
                for p in result.person_detections
            ]
            tracked_objects = tracker.update(detections)
            annotated_frame = _draw_detections_on_frame_with_tracking(
                frame.copy(), result, tracked_objects, optimized_pipeline
            )
            out.write(annotated_frame)
        else:
            out.write(frame)
    cap.release()
    out.release()
    return {"output_video": {"filename": output_filename, "path": output_path}}


def _bbox_overlap(bbox1, bbox2, threshold=0.5):
    if not bbox1 or not bbox2:
        return False
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])
    if x2 <= x1 or y2 <= y1:
        return False
    intersection = (x2 - x1) * (y2 - y1)
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union = area1 + area2 - intersection
    return (intersection / union) > threshold


def _draw_detections_on_frame_with_tracking(
    frame, result, tracked_objects, optimized_pipeline
):
    annotated_frame = frame.copy()
    pose_detector = optimized_pipeline.pose_detector
    if pose_detector is None:
        return annotated_frame
    pose_detector.detect(frame)
    washing_person_bboxes = [
        res["person_bbox"]
        for res in result.handwash_results
        if res.get("is_handwashing")
    ]
    for track in tracked_objects:
        bbox = track["bbox"]
        track_id = track["track_id"]
        label = f"编号:{track_id} (置信度:{track.get('confidence', 0.0):.2f})"
        cv2.rectangle(
            annotated_frame,
            (int(bbox[0]), int(bbox[1])),
            (int(bbox[2]), int(bbox[3])),
            (0, 255, 0),
            2,
        )
        cv2.putText(
            annotated_frame,
            label,
            (int(bbox[0]), int(bbox[1]) - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            2,
        )
    return annotated_frame


def _play_alert_sound():
    """在支持的系统上播放简易提示音（macOS优先）。"""
    try:
        # macOS 系统提示音
        if os.name == "posix" and os.uname().sysname == "Darwin":
            os.system("afplay /System/Library/Sounds/Glass.aiff >/dev/null 2>&1 &")
        else:
            # 其他平台退化为控制台蜂鸣
            print("\a", end="")
    except Exception:
        pass


def _anonymize_faces_or_head(image: np.ndarray) -> np.ndarray:
    """
    对传入图像进行打码：
    1) 优先使用Haar人脸检测进行区域模糊；
    2) 若未检测到人脸，则对上部区域（近似头部）进行模糊。
    """
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # 使用OpenCV自带的Haar特征分类器
        face_cascade_path = getattr(cv2, "data", None)
        if face_cascade_path is not None:
            cascade_file = os.path.join(
                cv2.data.haarcascades, "haarcascade_frontalface_default.xml"
            )
        else:
            cascade_file = "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_file)
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        anonymized = image.copy()
        if len(faces) > 0:
            for x, y, w, h in faces:
                x2, y2 = x + w, y + h
                roi = anonymized[y:y2, x:x2]
                if roi.size > 0:
                    roi = cv2.GaussianBlur(roi, (31, 31), 0)
                    anonymized[y:y2, x:x2] = roi
            return anonymized
        else:
            # 无人脸时，模糊图像上方40%的区域（近似头部）
            h = anonymized.shape[0]
            top_h = max(1, int(h * 0.4))
            roi = anonymized[0:top_h, :]
            if roi.size > 0:
                roi = cv2.GaussianBlur(roi, (31, 31), 0)
                anonymized[0:top_h, :] = roi
            return anonymized
    except Exception:
        return image


def _capture_violation(
    session, frame, track_id, violation_type, bbox, cooldown_period=10
):
    current_time = time.time()
    cooldown_key = (track_id, violation_type)
    last_capture_time = session.violation_cooldowns.get(cooldown_key, 0)
    if current_time - last_capture_time < cooldown_period:
        return
    try:
        timestamp = int(current_time)
        filename = f"{violation_type}_track_{track_id}_{timestamp}.jpg"
        output_dir = os.path.join("output", "violations", violation_type)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
        x1, y1, x2, y2 = map(int, bbox)
        cropped_image = frame[y1:y2, x1:x2]
        if cropped_image.size > 0:
            anonymized = _anonymize_faces_or_head(cropped_image)
            cv2.imwrite(output_path, anonymized)
            logger.info(f"Violation captured (anonymized): {filename}")
            session.violation_cooldowns[cooldown_key] = current_time
            _play_alert_sound()
    except Exception as e:
        logger.error(f"Failed to capture violation for track {track_id}: {e}")


def process_tracked_frame(session, frame, optimized_pipeline):
    time.time()
    person_detections = optimized_pipeline._detect_persons(frame)
    tracker_input = [
        {"bbox": p.get("bbox"), "confidence": p.get("confidence")}
        for p in person_detections
    ]
    tracked_objects = session.tracker.update(tracker_input)
    tracked_person_detections = []
    for tobj in tracked_objects:
        for pdet in person_detections:
            if _bbox_overlap(tobj["bbox"], pdet["bbox"], threshold=0.8):
                pdet["track_id"] = tobj["track_id"]
                tracked_person_detections.append(pdet)
                break
    hairnet_results = optimized_pipeline._detect_hairnet_for_persons(
        frame, tracked_person_detections
    )
    handwash_results = optimized_pipeline._detect_handwash_for_persons(
        frame, tracked_person_detections
    )
    sanitize_results = optimized_pipeline._detect_sanitize_for_persons(
        frame, tracked_person_detections
    )
    result = DetectionResult(
        person_detections=tracked_person_detections,
        hairnet_results=hairnet_results,
        handwash_results=handwash_results,
        sanitize_results=sanitize_results,
        processing_times={},
        annotated_image=None,
    )
    annotated_frame = _draw_detections_on_frame_with_tracking(
        frame.copy(), result, tracked_objects, optimized_pipeline
    )
    for tobj in tracked_objects:
        track_id = tobj["track_id"]
        person_bbox = tobj["bbox"]
        for h_res in hairnet_results:
            if _bbox_overlap(
                person_bbox, h_res.get("person_bbox", [])
            ) and not h_res.get("has_hairnet"):
                _capture_violation(session, frame, track_id, "no_hairnet", person_bbox)
                break
        is_washing = False
        for w_res in handwash_results:
            if _bbox_overlap(person_bbox, w_res.get("person_bbox", [])) and w_res.get(
                "is_handwashing"
            ):
                is_washing = True
                break
        if not is_washing:
            _capture_violation(session, frame, track_id, "not_handwashing", person_bbox)
    _, buffer = cv2.imencode(".jpg", annotated_frame)
    annotated_image_b64 = base64.b64encode(buffer.tobytes()).decode("utf-8")
    total_persons = len(tracked_objects)
    persons_with_hairnet = len(
        [h for h in hairnet_results if h.get("has_hairnet", False)]
    )
    persons_handwashing = len(
        [h for h in handwash_results if h.get("is_handwashing", False)]
    )
    persons_sanitizing = len(
        [s for s in sanitize_results if s.get("is_sanitizing", False)]
    )
    statistics = {
        "persons_with_hairnet": persons_with_hairnet,
        "persons_handwashing": persons_handwashing,
        "persons_sanitizing": persons_sanitizing,
    }
    detections = []
    for tobj in tracked_objects:
        detections.append(
            {
                "class": "person",
                "confidence": tobj.get("confidence", 0.0),
                "bbox": tobj.get("bbox", [0, 0, 0, 0]),
                "track_id": tobj.get("track_id"),
            }
        )
    end_time = time.time()
    return {
        "type": "comprehensive_detection_result",
        "detection_count": total_persons,
        "detections": detections,
        "statistics": statistics,
        "annotated_image": annotated_image_b64,
        "timestamp": end_time,
    }
