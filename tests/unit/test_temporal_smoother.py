"""
TemporalSmoother单元测试
"""

import pytest
import numpy as np

from src.core.temporal_smoother import TemporalSmoother


class TestTemporalSmoother:
    """TemporalSmoother测试类"""
    
    def test_initialization(self):
        """测试初始化"""
        smoother = TemporalSmoother(
            window_size=5,
            alpha=0.7,
            consistency_threshold=0.8,
        )
        
        assert smoother.window_size == 5
        assert smoother.alpha == 0.7
        assert smoother.consistency_threshold == 0.8
    
    def test_smooth_keypoints_single_frame(self):
        """测试单帧关键点平滑"""
        smoother = TemporalSmoother(window_size=5, alpha=0.7)
        
        keypoints = np.array([[100, 200], [150, 250], [200, 300]])
        confidences = np.array([0.9, 0.8, 0.7])
        
        smoothed_kpts, smoothed_conf = smoother.smooth_keypoints(
            "track_1", keypoints, confidences
        )
        
        # 单帧时，平滑后的结果应该与原始值相同
        assert np.allclose(smoothed_kpts, keypoints)
        assert np.allclose(smoothed_conf, confidences)
    
    def test_smooth_keypoints_multiple_frames(self):
        """测试多帧关键点平滑"""
        smoother = TemporalSmoother(window_size=5, alpha=0.7)
        
        # 第一帧
        keypoints1 = np.array([[100, 200], [150, 250]])
        confidences1 = np.array([0.9, 0.8])
        smoothed_kpts1, smoothed_conf1 = smoother.smooth_keypoints(
            "track_1", keypoints1, confidences1
        )
        
        # 第二帧（有变化）
        keypoints2 = np.array([[110, 210], [160, 260]])
        confidences2 = np.array([0.95, 0.85])
        smoothed_kpts2, smoothed_conf2 = smoother.smooth_keypoints(
            "track_1", keypoints2, confidences2
        )
        
        # 平滑后的值应该在原始值之间
        assert np.all(smoothed_kpts2 >= keypoints1)
        assert np.all(smoothed_kpts2 <= keypoints2)
        assert np.all(smoothed_conf2 >= confidences1)
        assert np.all(smoothed_conf2 <= confidences2)
    
    def test_smooth_keypoints_without_confidences(self):
        """测试没有置信度的关键点平滑"""
        smoother = TemporalSmoother(window_size=5, alpha=0.7)
        
        keypoints = np.array([[100, 200], [150, 250]])
        smoothed_kpts, smoothed_conf = smoother.smooth_keypoints(
            "track_1", keypoints, None
        )
        
        # 应该自动生成置信度（全1.0）
        assert len(smoothed_conf) == len(keypoints)
        assert np.all(smoothed_conf == 1.0)
    
    def test_check_consistency_stable(self):
        """测试一致性检查（稳定动作）"""
        smoother = TemporalSmoother(window_size=5, alpha=0.7)
        
        # 创建稳定的关键点序列（变化很小）
        base_keypoints = np.array([[100, 200], [150, 250]])
        for i in range(5):
            # 每帧只有很小的变化
            keypoints = base_keypoints + np.random.randn(*base_keypoints.shape) * 0.1
            smoother.smooth_keypoints("track_1", keypoints, None)
        
        # 检查一致性（应该很高）
        consistency = smoother.check_consistency("track_1", base_keypoints)
        assert consistency > 0.5  # 稳定动作应该有一致性
    
    def test_check_consistency_unstable(self):
        """测试一致性检查（不稳定动作）"""
        smoother = TemporalSmoother(window_size=5, alpha=0.7)
        
        # 创建不稳定的关键点序列（变化很大）
        for i in range(5):
            # 每帧都有很大的随机变化
            keypoints = np.random.rand(2, 2) * 1000
            smoother.smooth_keypoints("track_1", keypoints, None)
        
        # 检查一致性（应该较低）
        current_keypoints = np.random.rand(2, 2) * 1000
        consistency = smoother.check_consistency("track_1", current_keypoints)
        assert consistency < 1.0  # 不稳定动作一致性较低
    
    def test_check_consistency_no_history(self):
        """测试一致性检查（无历史）"""
        smoother = TemporalSmoother(window_size=5, alpha=0.7)
        
        # 没有历史时，应该返回1.0（认为一致）
        keypoints = np.array([[100, 200], [150, 250]])
        consistency = smoother.check_consistency("track_1", keypoints)
        assert consistency == 1.0
    
    def test_get_smoothed_keypoints(self):
        """测试获取平滑后的关键点"""
        smoother = TemporalSmoother(window_size=5, alpha=0.7)
        
        keypoints = np.array([[100, 200], [150, 250]])
        smoother.smooth_keypoints("track_1", keypoints, None)
        
        # 获取平滑后的关键点
        smoothed = smoother.get_smoothed_keypoints("track_1")
        assert smoothed is not None
        assert np.allclose(smoothed, keypoints)
    
    def test_reset_track(self):
        """测试重置track"""
        smoother = TemporalSmoother(window_size=5, alpha=0.7)
        
        # 添加一些数据
        keypoints = np.array([[100, 200], [150, 250]])
        smoother.smooth_keypoints("track_1", keypoints, None)
        
        # 重置
        smoother.reset_track("track_1")
        
        # 应该无法获取平滑后的关键点
        assert smoother.get_smoothed_keypoints("track_1") is None
    
    def test_reset_all(self):
        """测试重置所有"""
        smoother = TemporalSmoother(window_size=5, alpha=0.7)
        
        # 添加多个track的数据
        for i in range(3):
            keypoints = np.array([[100 + i, 200 + i], [150 + i, 250 + i]])
            smoother.smooth_keypoints(f"track_{i+1}", keypoints, None)
        
        # 重置所有
        smoother.reset_all()
        
        # 所有track都应该被清除
        for i in range(3):
            assert smoother.get_smoothed_keypoints(f"track_{i+1}") is None
    
    def test_window_size_limit(self):
        """测试窗口大小限制"""
        smoother = TemporalSmoother(window_size=3, alpha=0.7)
        
        # 添加超过窗口大小的帧
        for i in range(10):
            keypoints = np.array([[100 + i, 200 + i], [150 + i, 250 + i]])
            smoother.smooth_keypoints("track_1", keypoints, None)
        
        # 历史应该只保留最近3帧
        history = list(smoother.keypoint_history["track_1"])
        assert len(history) == 3
    
    def test_alpha_parameter(self):
        """测试alpha参数的影响"""
        # 高alpha（更依赖当前值）
        smoother_high = TemporalSmoother(window_size=5, alpha=0.9)
        
        # 低alpha（更依赖历史值）
        smoother_low = TemporalSmoother(window_size=5, alpha=0.1)
        
        # 第一帧
        keypoints1 = np.array([[100, 200], [150, 250]])
        smoother_high.smooth_keypoints("track_1", keypoints1, None)
        smoother_low.smooth_keypoints("track_2", keypoints1, None)
        
        # 第二帧（有很大变化）
        keypoints2 = np.array([[200, 300], [250, 350]])
        smoothed_high, _ = smoother_high.smooth_keypoints("track_1", keypoints2, None)
        smoothed_low, _ = smoother_low.smooth_keypoints("track_2", keypoints2, None)
        
        # 高alpha应该更接近当前值（keypoints2）
        # 低alpha应该更接近历史值（keypoints1）
        dist_high = np.linalg.norm(smoothed_high - keypoints2)
        dist_low = np.linalg.norm(smoothed_low - keypoints2)
        
        assert dist_high < dist_low  # 高alpha更接近当前值
    
    def test_get_stats(self):
        """测试获取统计信息"""
        smoother = TemporalSmoother(window_size=5, alpha=0.7)
        
        # 添加一些数据
        for i in range(3):
            keypoints = np.array([[100 + i, 200 + i], [150 + i, 250 + i]])
            smoother.smooth_keypoints(f"track_{i+1}", keypoints, None)
        
        stats = smoother.get_stats()
        assert stats["active_tracks"] == 3
        assert stats["window_size"] == 5
        assert stats["alpha"] == 0.7
        assert len(stats["tracks"]) == 3

