from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import asdict
from typing import Any, Deque, Dict, List, Optional, Tuple

import cv2


class CaptureService:
    def __init__(
        self,
        output_dir: str = "output/captures",
        pre_seconds: float = 2.0,
        post_seconds: float = 0.0,
        clip_fps: Optional[float] = None,
        save_crops: bool = True,
        anonymize_head: bool = False,
        anonymize_ratio: float = 0.4,
        blur_kernel: int = 31,
    ) -> None:
        self.output_dir = output_dir
        self.pre_seconds = max(0.0, float(pre_seconds))
        self.post_seconds = max(0.0, float(post_seconds))
        self.clip_fps = float(clip_fps) if clip_fps and clip_fps > 0 else 25.0
        self.save_crops = bool(save_crops)
        self.anonymize_head = bool(anonymize_head)
        self.anonymize_ratio = max(0.0, min(1.0, float(anonymize_ratio)))
        # blur_kernel 应为奇数
        self.blur_kernel = int(
            blur_kernel if int(blur_kernel) % 2 == 1 else int(blur_kernel) + 1
        )
        os.makedirs(self.output_dir, exist_ok=True)

    def save_event(
        self,
        event: Any,
        frame_bgr: Any,
        context: Dict[str, Any],
        buffer: Optional[Deque[Tuple[float, Any]]] = None,
    ) -> str:
        event_type = getattr(event, "type", context.get("type", "event"))
        track_id = int(getattr(event, "track_id", context.get("track_id", -1)))
        ts = float(getattr(event, "ts", time.time()))
        camera_id = str(context.get("camera_id") or "unknown")
        event_id = f"{int(ts)}_{event_type}_tid{track_id}"
        # 目录按 camera_id 分层，便于多路管理
        event_dir = os.path.join(self.output_dir, camera_id, event_id)
        os.makedirs(event_dir, exist_ok=True)

        # 元数据
        meta = {
            "type": event_type,
            "track_id": track_id,
            "ts": ts,
            "evidence": getattr(event, "evidence", context.get("evidence", {})) or {},
            "region": context.get("region"),
            "has_hairnet": context.get("has_hairnet"),
            "camera_id": camera_id,
        }
        with open(os.path.join(event_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 快照（原图 + 匿名化版本）
        snap_path = os.path.join(event_dir, "snapshot.jpg")
        try:
            cv2.imwrite(snap_path, frame_bgr)
        except Exception:
            pass
        try:
            if self.anonymize_head:
                anon = self._anonymize_head_region(
                    frame_bgr.copy(), context.get("bbox")
                )
                cv2.imwrite(os.path.join(event_dir, "snapshot_anon.jpg"), anon)
        except Exception:
            pass

        # 裁剪
        bbox = context.get("bbox")
        if self.save_crops and isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            try:
                x1, y1, x2, y2 = [int(v) for v in bbox[:4]]
                h, w = frame_bgr.shape[:2]
                x1 = max(0, min(x1, w - 1))
                x2 = max(0, min(x2, w - 1))
                y1 = max(0, min(y1, h - 1))
                y2 = max(0, min(y2, h - 1))
                if x2 > x1 and y2 > y1:
                    crop = frame_bgr[y1:y2, x1:x2]
                    cv2.imwrite(os.path.join(event_dir, "crop.jpg"), crop)
                    if self.anonymize_head:
                        try:
                            crop_anon = self._anonymize_head_region(
                                crop.copy(), [0, 0, crop.shape[1], crop.shape[0]]
                            )
                            cv2.imwrite(
                                os.path.join(event_dir, "crop_anon.jpg"), crop_anon
                            )
                        except Exception:
                            pass
            except Exception:
                pass

        # 片段（仅使用事件前窗口 + 当前帧）
        if buffer and (self.pre_seconds > 0.0 or self.post_seconds > 0.0):
            start_ts = ts - float(self.pre_seconds)
            end_ts = ts  # 简化：暂不等待后窗口
            seg: List[Any] = []
            try:
                for ts_i, frm in list(buffer):
                    if ts_i >= start_ts and ts_i <= end_ts:
                        seg.append(frm)
                # 至少若干帧再写视频
                if len(seg) >= max(3, int(self.clip_fps * 0.3)):
                    h, w = seg[0].shape[:2]
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    out_path = os.path.join(event_dir, "clip_pre.mp4")
                    vw = cv2.VideoWriter(out_path, fourcc, self.clip_fps, (w, h))
                    for frm in seg:
                        vw.write(frm)
                    vw.release()
            except Exception:
                pass

        return event_dir

    def _anonymize_head_region(self, image, bbox):
        try:
            h, w = image.shape[:2]
            if not bbox or not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
                # 无人框时按整图上部区域模糊
                x1, y1, x2, y2 = 0, 0, w, int(h * self.anonymize_ratio)
            else:
                x1, y1, x2, y2 = [int(b) for b in bbox[:4]]
                # 人框的上部区域（头肩区域）
                head_h = max(1, int((y2 - y1) * self.anonymize_ratio))
                y2 = y1 + head_h
                x1 = max(0, min(x1, w - 1))
                x2 = max(0, min(x2, w - 1))
                y1 = max(0, min(y1, h - 1))
                y2 = max(0, min(y2, h - 1))
            if x2 > x1 and y2 > y1:
                roi = image[y1:y2, x1:x2]
                # 高斯模糊
                blurred = cv2.GaussianBlur(roi, (self.blur_kernel, self.blur_kernel), 0)
                image[y1:y2, x1:x2] = blurred
            return image
        except Exception:
            return image
