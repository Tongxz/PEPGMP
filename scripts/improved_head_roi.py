"""
增强的头部ROI提取器
Enhanced Head ROI Extractor for better hairnet detection
"""

import cv2
import numpy as np
from typing import Tuple, List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ImprovedHeadROIExtractor:
    """增强的头部ROI提取器"""
    
    def __init__(self, 
                 head_expansion_ratio: float = 0.3,
                 min_head_area: float = 0.01,
                 max_head_area: float = 0.25,
                 aspect_ratio_range: Tuple[float, float] = (0.5, 2.0)):
        """
        初始化增强的头部ROI提取器
        
        Args:
            head_expansion_ratio: 头部区域扩展比例
            min_head_area: 最小头部区域占比
            max_head_area: 最大头部区域占比
            aspect_ratio_range: 头部区域宽高比范围
        """
        self.head_expansion_ratio = head_expansion_ratio
        self.min_head_area = min_head_area
        self.max_head_area = max_head_area
        self.aspect_ratio_range = aspect_ratio_range
        
    def extract_head_roi(self, 
                        image: np.ndarray, 
                        pose_landmarks: List[Dict[str, Any]],
                        face_bbox: Optional[Tuple[int, int, int, int]] = None) -> List[Tuple[int, int, int, int]]:
        """
        从图像中提取增强的头部ROI区域
        
        Args:
            image: 输入图像
            pose_landmarks: 姿态关键点
            face_bbox: 可选的人脸边界框
            
        Returns:
            头部ROI区域列表 [(x, y, w, h), ...]
        """
        if not pose_landmarks:
            logger.warning("没有检测到姿态关键点")
            return []
            
        height, width = image.shape[:2]
        head_rois = []
        
        for landmarks in pose_landmarks:
            try:
                # 提取头部关键点
                head_roi = self._extract_single_head_roi(
                    landmarks, width, height, face_bbox
                )
                
                if head_roi:
                    # 验证ROI区域
                    if self._validate_roi(head_roi, width, height):
                        head_rois.append(head_roi)
                        
            except Exception as e:
                logger.error(f"提取头部ROI时出错: {e}")
                continue
                
        return head_rois
    
    def _extract_single_head_roi(self, 
                                landmarks: Dict[str, Any],
                                width: int, 
                                height: int,
                                face_bbox: Optional[Tuple[int, int, int, int]] = None) -> Optional[Tuple[int, int, int, int]]:
        """
        从单个人的关键点提取头部ROI
        
        Args:
            landmarks: 单个人的关键点数据
            width: 图像宽度
            height: 图像高度
            face_bbox: 可选的人脸边界框
            
        Returns:
            头部ROI (x, y, w, h) 或 None
        """
        try:
            # 如果有人脸边界框，优先使用
            if face_bbox:
                x, y, w, h = face_bbox
                # 扩展人脸区域到头部
                expansion = int(min(w, h) * self.head_expansion_ratio)
                x = max(0, x - expansion)
                y = max(0, y - expansion)
                w = min(width - x, w + 2 * expansion)
                h = min(height - y, h + 2 * expansion)
                return (x, y, w, h)
            
            # 使用姿态关键点估计头部区域
            if 'landmark' in landmarks:
                # MediaPipe格式
                return self._extract_from_mediapipe_landmarks(landmarks['landmark'], width, height)
            elif 'keypoints' in landmarks:
                # OpenPose格式
                return self._extract_from_openpose_landmarks(landmarks['keypoints'], width, height)
            else:
                logger.warning("不支持的关键点格式")
                return None
                
        except Exception as e:
            logger.error(f"提取单个头部ROI时出错: {e}")
            return None
    
    def _extract_from_mediapipe_landmarks(self, 
                                        landmarks: List[Dict],
                                        width: int, 
                                        height: int) -> Optional[Tuple[int, int, int, int]]:
        """从MediaPipe关键点提取头部ROI"""
        try:
            # 头部关键点索引 (MediaPipe Pose)
            head_indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # 面部关键点
            
            x_coords = []
            y_coords = []
            
            for idx in head_indices:
                if idx < len(landmarks):
                    landmark = landmarks[idx]
                    if landmark.get('visibility', 0) > 0.5:  # 可见性阈值
                        x_coords.append(int(landmark['x'] * width))
                        y_coords.append(int(landmark['y'] * height))
            
            if len(x_coords) < 3:  # 至少需要3个点
                return None
                
            # 计算边界框
            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)
            
            # 扩展头部区域
            head_width = max_x - min_x
            head_height = max_y - min_y
            expansion_x = int(head_width * self.head_expansion_ratio)
            expansion_y = int(head_height * self.head_expansion_ratio)
            
            x = max(0, min_x - expansion_x)
            y = max(0, min_y - expansion_y)
            w = min(width - x, head_width + 2 * expansion_x)
            h = min(height - y, head_height + 2 * expansion_y)
            
            return (x, y, w, h)
            
        except Exception as e:
            logger.error(f"从MediaPipe关键点提取头部ROI时出错: {e}")
            return None
    
    def _extract_from_openpose_landmarks(self, 
                                       keypoints: List[float],
                                       width: int, 
                                       height: int) -> Optional[Tuple[int, int, int, int]]:
        """从OpenPose关键点提取头部ROI"""
        try:
            # OpenPose头部关键点索引
            head_indices = [0, 1, 2, 3, 4, 14, 15, 16, 17]  # 面部和头部关键点
            
            x_coords = []
            y_coords = []
            
            for idx in head_indices:
                if idx * 3 + 2 < len(keypoints):
                    x = keypoints[idx * 3]
                    y = keypoints[idx * 3 + 1]
                    confidence = keypoints[idx * 3 + 2]
                    
                    if confidence > 0.3:  # 置信度阈值
                        x_coords.append(int(x * width))
                        y_coords.append(int(y * height))
            
            if len(x_coords) < 3:
                return None
                
            # 计算边界框
            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)
            
            # 扩展头部区域
            head_width = max_x - min_x
            head_height = max_y - min_y
            expansion_x = int(head_width * self.head_expansion_ratio)
            expansion_y = int(head_height * self.head_expansion_ratio)
            
            x = max(0, min_x - expansion_x)
            y = max(0, min_y - expansion_y)
            w = min(width - x, head_width + 2 * expansion_x)
            h = min(height - y, head_height + 2 * expansion_y)
            
            return (x, y, w, h)
            
        except Exception as e:
            logger.error(f"从OpenPose关键点提取头部ROI时出错: {e}")
            return None
    
    def _validate_roi(self, 
                     roi: Tuple[int, int, int, int],
                     image_width: int, 
                     image_height: int) -> bool:
        """
        验证ROI区域是否合理
        
        Args:
            roi: ROI区域 (x, y, w, h)
            image_width: 图像宽度
            image_height: 图像高度
            
        Returns:
            是否为有效ROI
        """
        x, y, w, h = roi
        
        # 检查边界
        if x < 0 or y < 0 or x + w > image_width or y + h > image_height:
            return False
            
        # 检查最小尺寸
        if w < 10 or h < 10:
            return False
            
        # 检查面积比例
        roi_area = w * h
        image_area = image_width * image_height
        area_ratio = roi_area / image_area
        
        if area_ratio < self.min_head_area or area_ratio > self.max_head_area:
            return False
            
        # 检查宽高比
        aspect_ratio = w / h
        if (aspect_ratio < self.aspect_ratio_range[0] or 
            aspect_ratio > self.aspect_ratio_range[1]):
            return False
            
        return True
    
    def visualize_head_rois(self, 
                           image: np.ndarray,
                           head_rois: List[Tuple[int, int, int, int]],
                           color: Tuple[int, int, int] = (0, 255, 0),
                           thickness: int = 2) -> np.ndarray:
        """
        在图像上可视化头部ROI区域
        
        Args:
            image: 输入图像
            head_rois: 头部ROI列表
            color: 绘制颜色 (B, G, R)
            thickness: 线条粗细
            
        Returns:
            绘制了ROI的图像
        """
        vis_image = image.copy()
        
        for i, (x, y, w, h) in enumerate(head_rois):
            # 绘制矩形框
            cv2.rectangle(vis_image, (x, y), (x + w, y + h), color, thickness)
            
            # 添加标签
            label = f"Head_{i+1}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            cv2.rectangle(vis_image, 
                         (x, y - label_size[1] - 5), 
                         (x + label_size[0], y), 
                         color, -1)
            cv2.putText(vis_image, label, (x, y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return vis_image
