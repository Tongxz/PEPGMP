import logging
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class Track:
    """单个追踪目标"""

    def __init__(self, track_id: int, bbox: List[int], confidence: float):
        self.track_id = track_id
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.confidence = confidence
        self.age = 0
        self.hits = 1
        self.time_since_update = 0
        self.history = deque(maxlen=30)  # 保存历史位置
        self.history.append(bbox)
        self.state = "active"  # active, lost, deleted

    def update(self, bbox: List[int], confidence: float):
        """更新追踪目标"""
        self.bbox = bbox
        self.confidence = confidence
        self.hits += 1
        self.time_since_update = 0
        self.history.append(bbox)
        self.state = "active"

    def predict(self):
        """预测下一帧位置（简单线性预测）"""
        if len(self.history) < 2:
            return self.bbox

        # 计算速度
        prev_bbox = self.history[-2]
        curr_bbox = self.history[-1]

        dx = curr_bbox[0] - prev_bbox[0]
        dy = curr_bbox[1] - prev_bbox[1]

        # 预测下一帧位置
        predicted_bbox = [
            curr_bbox[0] + dx,
            curr_bbox[1] + dy,
            curr_bbox[2] + dx,
            curr_bbox[3] + dy,
        ]

        return predicted_bbox

    def get_center(self) -> Tuple[float, float]:
        """获取边界框中心点"""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def get_area(self) -> float:
        """获取边界框面积"""
        x1, y1, x2, y2 = self.bbox
        return (x2 - x1) * (y2 - y1)


class MultiObjectTracker:
    """多目标追踪器

    基于IoU匹配的简单追踪算法
    """

    def __init__(self, max_disappeared: int = 10, iou_threshold: float = 0.3,
                 dist_threshold: float = 200.0, match_strategy: str = "hungarian",
                 iou_weight: float = 0.6, recycle_ids: bool = False,
                 force_revival: bool = False, force_revival_dist: Optional[float] = None):
        """
        初始化追踪器

        Args:
            max_disappeared: 目标消失的最大帧数
            iou_threshold: IoU匹配阈值
        """
        self.tracks = {}
        self.next_id = 1
        self.max_disappeared = max_disappeared
        self.iou_threshold = iou_threshold
        self.dist_threshold = dist_threshold
        self.match_strategy = match_strategy  # 'hungarian' or 'greedy'
        self.iou_weight = iou_weight  # 0..1, remaining weight for distance
        self.recycle_ids = recycle_ids
        self.force_revival = force_revival
        self.force_revival_dist = force_revival_dist if force_revival_dist is not None else dist_threshold * 1.5
        self._recycle_pool: List[int] = []

        logger.info(
            f"MultiObjectTracker initialized with IoU threshold: {iou_threshold}, dist_threshold: {dist_threshold}, strategy: {match_strategy}, iou_weight: {iou_weight}, recycle_ids: {recycle_ids}, force_revival: {force_revival}"
        )

    def calculate_iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        """计算两个边界框的IoU"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2

        # 计算交集
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)

        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0

        intersection = (x2_i - x1_i) * (y2_i - y1_i)

        # 计算并集
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def update(self, detections: List[Dict]) -> List[Dict]:
        """
        更新追踪器

        Args:
            detections: 当前帧的检测结果

        Returns:
            追踪结果列表
        """
        # 如果没有检测结果，更新所有追踪目标的状态（不输出未匹配tracks）
        if not detections:
            for track in self.tracks.values():
                track.time_since_update += 1
                track.age += 1
                if track.time_since_update > self.max_disappeared:
                    track.state = "lost"
            return []

        # 计算IoU矩阵与中心距离矩阵
        track_ids = list(self.tracks.keys())
        iou_matrix = np.zeros((len(track_ids), len(detections)))
        dist_matrix = np.zeros((len(track_ids), len(detections)))

        for i, track_id in enumerate(track_ids):
            track = self.tracks[track_id]
            predicted_bbox = track.predict()

            for j, detection in enumerate(detections):
                iou = self.calculate_iou(predicted_bbox, detection["bbox"])
                iou_matrix[i, j] = iou
                # 计算中心距离
                tx, ty = ((predicted_bbox[0] + predicted_bbox[2]) / 2.0, (predicted_bbox[1] + predicted_bbox[3]) / 2.0)
                db = detection["bbox"]
                dx, dy = ((db[0] + db[2]) / 2.0, (db[1] + db[3]) / 2.0)
                dist_matrix[i, j] = np.hypot(tx - dx, ty - dy)

        # 构造融合代价矩阵：cost = iou_weight*(1 - IoU) + (1-iou_weight)*min(1, dist/dist_threshold)
        # 注意：匈牙利算法求最小代价
        if len(track_ids) > 0 and len(detections) > 0:
            norm_dist = np.clip(dist_matrix / max(1e-5, self.dist_threshold), 0.0, 1.0)
            cost_matrix = self.iou_weight * (1.0 - iou_matrix) + (1.0 - self.iou_weight) * norm_dist
        else:
            cost_matrix = np.zeros_like(iou_matrix)

        # 匹配追踪目标和检测结果
        matched_tracks, matched_detections = self._match_tracks_detections(
            iou_matrix, dist_matrix, cost_matrix, track_ids, detections
        )

        # 更新匹配的追踪目标
        for track_idx, det_idx in zip(matched_tracks, matched_detections):
            track_id = track_ids[track_idx]
            detection = detections[det_idx]
            self.tracks[track_id].update(detection["bbox"], detection["confidence"])

        # 计算未匹配的track集合（索引与ID）
        unmatched_track_indices = set(range(len(track_ids))) - set(matched_tracks)
        id_to_index = {tid: idx for idx, tid in enumerate(track_ids)}
        unmatched_track_ids = {track_ids[idx] for idx in unmatched_track_indices}

        # 尝试“距离复活”：优先复用本帧未匹配的旧track，其次复活非active的track；否则创建新track
        unmatched_detections = list(set(range(len(detections))) - set(matched_detections))
        revived_infos = []  # 收集本帧复活并更新的track信息，纳入输出
        revived_track_ids = set()
        for det_idx in unmatched_detections:
            detection = detections[det_idx]
            db = detection["bbox"]
            dx, dy = ((db[0] + db[2]) / 2.0, (db[1] + db[3]) / 2.0)
            # 查找最近的非active(track.state != 'active')的track
            best_tid: Optional[int] = None
            best_dist = float("inf")
            for tid, tr in self.tracks.items():
                # 允许候选：1) 本帧未匹配的旧track（即便仍标记active），或 2) 非active/lost的track
                if not (tid in unmatched_track_ids or tr.state != "active"):
                    continue
                if tid in revived_track_ids:
                    continue
                tx, ty = tr.get_center()
                dist = np.hypot(tx - dx, ty - dy)
                if dist < best_dist:
                    best_dist = dist
                    best_tid = tid
            # 允许强制复活更宽松的距离阈值
            revival_limit = self.force_revival_dist if self.force_revival else self.dist_threshold
            if best_tid is not None and best_dist <= revival_limit:
                # 复活该track并更新
                tr = self.tracks[best_tid]
                tr.update(detection["bbox"], detection["confidence"])
                revived_infos.append({
                    "track_id": tr.track_id,
                    "bbox": tr.bbox,
                    "confidence": tr.confidence,
                    "age": tr.age,
                    "hits": tr.hits,
                })
                revived_track_ids.add(best_tid)
                # 若该track属于本帧未匹配集合，从未匹配集合中移除，避免后续miss递增
                if best_tid in unmatched_track_ids:
                    unmatched_track_ids.remove(best_tid)
                    # 同步移除其索引
                    idx = id_to_index.get(best_tid)
                    if idx is not None and idx in unmatched_track_indices:
                        unmatched_track_indices.remove(idx)
            else:
                # 创建新track，尝试回收旧ID
                if self.recycle_ids and self._recycle_pool:
                    reuse_id = min(self._recycle_pool)
                    self._recycle_pool.remove(reuse_id)
                    new_track = Track(reuse_id, detection["bbox"], detection["confidence"])
                    self.tracks[reuse_id] = new_track
                else:
                    new_track = Track(self.next_id, detection["bbox"], detection["confidence"])
                    self.tracks[self.next_id] = new_track
                    self.next_id += 1

        # 更新未匹配的追踪目标（标记missed，不纳入本帧输出）
        for track_idx in unmatched_track_indices:
            track_id = track_ids[track_idx]
            track = self.tracks[track_id]
            track.time_since_update += 1
            track.age += 1
            if track.time_since_update > self.max_disappeared:
                track.state = "lost"

        # 删除长时间丢失的追踪目标
        self._cleanup_tracks()

        # 仅返回本帧成功匹配并更新的tracks（含“复活”的tracks）
        current_active = []
        for track_idx, det_idx in zip(matched_tracks, matched_detections):
            tid = track_ids[track_idx]
            t = self.tracks[tid]
            current_active.append({
                "track_id": t.track_id,
                "bbox": t.bbox,
                "confidence": t.confidence,
                "age": t.age,
                "hits": t.hits,
            })
        # 合并复活的tracks到输出
        if revived_infos:
            current_active.extend(revived_infos)
        return current_active

    def _match_tracks_detections(
        self, iou_matrix: np.ndarray, dist_matrix: np.ndarray, cost_matrix: np.ndarray, track_ids: List[int], detections: List[Dict]
    ) -> Tuple[List[int], List[int]]:
        """匹配追踪目标和检测结果（支持匈牙利或贪心），并应用IoU与距离门限"""
        num_t = len(track_ids)
        num_d = len(detections)
        if num_t == 0 or num_d == 0:
            return [], []

        # 使用匈牙利算法最小化代价
        matched_tracks: List[int] = []
        matched_detections: List[int] = []

        if self.match_strategy == "hungarian":
            try:
                from scipy.optimize import linear_sum_assignment
                row_ind, col_ind = linear_sum_assignment(cost_matrix)
                for r, c in zip(row_ind, col_ind):
                    iou = iou_matrix[r, c]
                    dist = dist_matrix[r, c]
                    # 放宽门限：IoU 或 距离 其一满足即可
                    if (iou >= self.iou_threshold) or (dist <= self.dist_threshold):
                        matched_tracks.append(r)
                        matched_detections.append(c)
            except Exception:
                # 回退到贪心
                matched_tracks, matched_detections = self._greedy_match(iou_matrix, dist_matrix)
        else:
            matched_tracks, matched_detections = self._greedy_match(iou_matrix, dist_matrix)

        return matched_tracks, matched_detections

    def _greedy_match(self, iou_matrix: np.ndarray, dist_matrix: np.ndarray) -> Tuple[List[int], List[int]]:
        matched_tracks: List[int] = []
        matched_detections: List[int] = []
        available_track_indices = list(range(iou_matrix.shape[0]))
        available_det_indices = list(range(iou_matrix.shape[1]))
        mat_iou = iou_matrix.copy()
        mat_dist = dist_matrix.copy()
        # 第一阶段：按IoU贪心匹配
        while mat_iou.size:
            max_iou_idx = np.unravel_index(np.argmax(mat_iou), mat_iou.shape)
            max_iou = mat_iou[max_iou_idx]
            if max_iou < self.iou_threshold:
                break
            r, c = max_iou_idx
            matched_tracks.append(available_track_indices[r])
            matched_detections.append(available_det_indices[c])
            mat_iou = np.delete(mat_iou, r, axis=0)
            mat_iou = np.delete(mat_iou, c, axis=1)
            mat_dist = np.delete(mat_dist, r, axis=0)
            mat_dist = np.delete(mat_dist, c, axis=1)
            available_track_indices.pop(r)
            available_det_indices.pop(c)

        # 第二阶段：对剩余未匹配，按距离最小但在阈值内匹配
        while mat_dist.size:
            min_dist_idx = np.unravel_index(np.argmin(mat_dist), mat_dist.shape)
            min_dist = mat_dist[min_dist_idx]
            if min_dist > self.dist_threshold:
                break
            r, c = min_dist_idx
            matched_tracks.append(available_track_indices[r])
            matched_detections.append(available_det_indices[c])
            mat_dist = np.delete(mat_dist, r, axis=0)
            mat_dist = np.delete(mat_dist, c, axis=1)
            mat_iou = np.delete(mat_iou, r, axis=0) if mat_iou.size else mat_iou
            mat_iou = np.delete(mat_iou, c, axis=1) if mat_iou.size else mat_iou
            available_track_indices.pop(r)
            available_det_indices.pop(c)
        return matched_tracks, matched_detections

    def _cleanup_tracks(self):
        """清理长时间丢失的追踪目标"""
        to_delete = []
        for track_id, track in self.tracks.items():
            if track.time_since_update > self.max_disappeared * 2:
                to_delete.append(track_id)

        for track_id in to_delete:
            if self.recycle_ids:
                # 回收可用ID
                self._recycle_pool.append(track_id)
            del self.tracks[track_id]

    def _get_active_tracks(self) -> List[Dict]:
        """获取活跃的追踪目标"""
        active_tracks = []
        for track in self.tracks.values():
            if track.state == "active":
                track_info = {
                    "track_id": track.track_id,
                    "bbox": track.bbox,
                    "confidence": track.confidence,
                    "age": track.age,
                    "hits": track.hits,
                }
                active_tracks.append(track_info)

        return active_tracks

    def get_track_history(self, track_id: int) -> List[List[int]]:
        """获取指定追踪目标的历史轨迹"""
        if track_id in self.tracks:
            return list(self.tracks[track_id].history)
        return []

    def reset(self):
        """重置追踪器"""
        self.tracks.clear()
        self.next_id = 1
        logger.info("MultiObjectTracker reset")
