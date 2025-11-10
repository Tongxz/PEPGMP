"""
检测循环服务 - 应用服务层

负责协调检测循环的执行，包括：
- 视频帧读取
- 检测处理
- 结果保存
- 视频流推送
- 性能统计
"""

from __future__ import annotations

import logging
import platform
import signal
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Optional

import cv2
import numpy as np

from src.application.detection_application_service import DetectionApplicationService
from src.application.video_stream_application_service import (
    VideoStreamApplicationService,
)
from src.core.optimized_detection_pipeline import OptimizedDetectionPipeline

logger = logging.getLogger(__name__)


class DetectionLoopConfig:
    """检测循环配置"""

    def __init__(
        self,
        camera_id: str,
        source: str,
        log_interval: int = 1,
        stream_interval: int = 3,
        video_quality: int = 60,
        stream_width: int = 800,
        stream_height: int = 450,
    ):
        self.camera_id = camera_id
        self.source = source
        self.log_interval = log_interval
        self.stream_interval = stream_interval
        self.video_quality = video_quality
        self.stream_width = stream_width
        self.stream_height = stream_height


class DetectionLoopService:
    """
    检测循环服务 - 应用服务层

    职责：
    1. 管理视频源的打开和释放
    2. 协调检测管线、应用服务、视频流服务
    3. 处理优雅退出信号
    4. 统计性能指标

    不包含：
    - 具体的检测逻辑（由 OptimizedDetectionPipeline 处理）
    - 保存逻辑（由 DetectionApplicationService 处理）
    - 视频流推送逻辑（由 VideoStreamApplicationService 处理）
    """

    def __init__(
        self,
        config: DetectionLoopConfig,
        detection_pipeline: OptimizedDetectionPipeline,
        detection_app_service: Optional[DetectionApplicationService] = None,
        video_stream_service: Optional[VideoStreamApplicationService] = None,
    ):
        """
        初始化检测循环服务

        Args:
            config: 检测循环配置
            detection_pipeline: 检测管线
            detection_app_service: 检测应用服务（可选，用于保存）
            video_stream_service: 视频流服务（可选，用于推送视频）
        """
        self.config = config
        self.detection_pipeline = detection_pipeline
        self.detection_app_service = detection_app_service
        self.video_stream_service = video_stream_service

        # 状态
        self.shutdown_requested = False
        self.resources = {"cap": None}  # 使用字典存储，便于信号处理器访问

        # 统计
        self.frame_count = 0
        self.process_count = 0
        self.start_time = None
        self.hour_stats = defaultdict(int)
        self.current_hour = None

        # 注册信号处理器
        self._register_signal_handlers()

        logger.info(
            f"检测循环服务已初始化: camera={config.camera_id}, "
            f"stream_interval={config.stream_interval}, "
            f"video_stream_service={'已配置' if video_stream_service else '未配置'}"
        )

    def _register_signal_handlers(self):
        """注册信号处理器"""

        def signal_handler(signum, frame):
            """处理退出信号"""
            logger.info(f"收到信号 {signum}，准备退出...")
            self.shutdown_requested = True

            # 立即尝试释放摄像头
            try:
                cap_obj = self.resources.get("cap")
                if cap_obj is not None and cap_obj.isOpened():
                    logger.info("收到退出信号，立即释放摄像头...")
                    cap_obj.release()

                    # 在macOS上，需要额外的清理
                    if platform.system() == "Darwin":
                        time.sleep(0.1)
                        cv2.destroyAllWindows()
            except Exception as e:
                logger.debug(f"信号处理器中释放摄像头失败: {e}")

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def _open_video_source(self) -> cv2.VideoCapture:
        """
        打开视频源

        Returns:
            VideoCapture对象

        Raises:
            RuntimeError: 无法打开视频源
        """
        source = self.config.source

        # 尝试将源转换为整数（摄像头索引）
        try:
            source = int(source)
        except (ValueError, TypeError):
            pass  # 保持为字符串（文件路径）

        cap = cv2.VideoCapture(source)
        self.resources["cap"] = cap  # 存储到字典中，以便信号处理器访问

        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频源: {self.config.source}")

        # 获取视频信息
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        logger.info(
            f"视频信息: {width}x{height} @ {fps}FPS, "
            f"总帧数: {total_frames if total_frames > 0 else '未知(实时流)'}"
        )

        return cap

    def _release_video_source(self, cap: cv2.VideoCapture):
        """
        释放视频源

        Args:
            cap: VideoCapture对象
        """
        logger.info("释放资源...")

        try:
            cap_obj = self.resources.get("cap") or cap
            if cap_obj is not None:
                try:
                    if cap_obj.isOpened():
                        cap_obj.release()
                        logger.info("摄像头已释放")
                    else:
                        logger.debug("摄像头已关闭")
                except Exception as e:
                    logger.warning(f"释放摄像头时出错: {e}")
                    # 即使出错也尝试再次释放
                    try:
                        cap_obj.release()
                    except Exception:
                        pass

                # 在macOS上，需要额外的清理步骤
                if platform.system() == "Darwin":
                    time.sleep(0.2)

                # 清空引用
                self.resources["cap"] = None
        except Exception as e:
            logger.error(f"释放摄像头失败: {e}")
        finally:
            try:
                cv2.destroyAllWindows()
            except Exception as e:
                logger.debug(f"关闭窗口失败（可能没有窗口）: {e}")

        logger.info("资源释放完成")

    async def _process_frame(
        self, frame: np.ndarray, frame_count: int
    ) -> Dict[str, Any]:
        """
        处理单个帧

        Args:
            frame: 视频帧
            frame_count: 帧编号

        Returns:
            处理结果
        """
        # 1. 执行检测
        result = self.detection_pipeline.detect_comprehensive(frame)

        # 2. 保存记录（如果配置了应用服务）
        saved_to_db = False
        save_reason = None

        if self.detection_app_service:
            try:
                app_result = await self.detection_app_service.process_realtime_stream(
                    camera_id=self.config.camera_id,
                    frame=frame,
                    frame_count=frame_count,
                )
                saved_to_db = app_result.get("saved_to_db", False)
                save_reason = app_result.get("save_reason")

                if saved_to_db:
                    logger.debug(
                        f"✓ 帧 {frame_count}: 已保存 ({save_reason}), "
                        f"违规={app_result['result']['has_violations']}, "
                        f"严重程度={app_result['result']['violation_severity']:.2f}"
                    )
            except Exception as e:
                logger.error(f"保存帧失败: {e}")

        # 3. 推送视频流（如果配置了视频流服务）
        if self.video_stream_service and frame_count % self.config.stream_interval == 0:
            try:
                # 判断是否有标注
                annotated_frame = (
                    result.annotated_frame
                    if hasattr(result, "annotated_frame")
                    else None
                )
                has_annotations = annotated_frame is not None

                # 使用标注后的帧（如果有）或原始帧
                frame_to_push = annotated_frame if has_annotations else frame

                logger.info(
                    f"准备推送视频帧: camera={self.config.camera_id}, "
                    f"frame={frame_count}, interval={self.config.stream_interval}, "
                    f"has_annotations={has_annotations}"
                )

                success = await self.video_stream_service.push_frame(
                    camera_id=self.config.camera_id,
                    frame=frame_to_push,
                    quality=self.config.video_quality,
                    target_width=self.config.stream_width,
                    target_height=self.config.stream_height,
                )

                if success:
                    logger.info(
                        f"视频帧推送成功: camera={self.config.camera_id}, frame={frame_count}"
                    )
                else:
                    logger.warning(
                        f"视频帧推送失败: camera={self.config.camera_id}, frame={frame_count}"
                    )
            except Exception as e:
                logger.error(
                    f"推送视频流失败: camera={self.config.camera_id}, frame={frame_count}, error={e}",
                    exc_info=True,
                )

        return {
            "result": result,
            "saved_to_db": saved_to_db,
            "save_reason": save_reason,
        }

    def _update_statistics(self, frame_count: int):
        """
        更新统计信息

        Args:
            frame_count: 当前帧数
        """
        now = datetime.now()
        new_hour = now.replace(minute=0, second=0, microsecond=0)

        if self.current_hour is None:
            self.current_hour = new_hour

        if new_hour != self.current_hour:
            # 小时变化，记录统计
            logger.info(
                f"小时统计: {self.current_hour.strftime('%Y-%m-%d %H:00')} - "
                f"处理帧数: {self.hour_stats[self.current_hour]}"
            )
            self.current_hour = new_hour

        self.hour_stats[new_hour] += 1

        # 每100帧输出性能统计
        if frame_count % 100 == 0:
            elapsed = time.time() - self.start_time
            avg_fps = self.process_count / elapsed if elapsed > 0 else 0
            logger.info(
                f"性能统计: 帧数={frame_count}, 处理数={self.process_count}, "
                f"平均FPS={avg_fps:.2f}, 运行时间={elapsed:.1f}s"
            )

    async def run(self):
        """
        运行检测循环

        主循环：
        1. 打开视频源
        2. 循环读取帧
        3. 处理帧（检测、保存、推送）
        4. 更新统计
        5. 优雅退出时释放资源
        """
        cap = None

        try:
            # 打开视频源
            cap = self._open_video_source()
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            self.start_time = time.time()
            self.frame_count = 0
            self.process_count = 0

            logger.info("开始视频处理循环...")

            # 主循环
            while not self.shutdown_requested:
                # 检查摄像头是否已关闭
                if not cap.isOpened():
                    logger.warning("摄像头已关闭，退出循环")
                    break

                # 读取帧
                ret, frame = cap.read()
                if not ret:
                    if total_frames > 0:
                        # 视频文件播放完成，重新开始
                        logger.info("视频文件播放完成，重新开始循环播放...")
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        self.frame_count = 0
                        continue
                    else:
                        logger.warning("视频流读取失败")
                        break

                self.frame_count += 1

                # 跳帧处理：只对检测和保存逻辑跳过，视频流推送不受影响
                should_process_detection = (
                    self.config.log_interval == 1
                    or self.frame_count % self.config.log_interval == 0
                )

                if should_process_detection:
                    self.process_count += 1
                    # 处理帧（检测和保存）
                    try:
                        await self._process_frame(frame, self.frame_count)
                    except Exception as e:
                        logger.error(f"处理帧 {self.frame_count} 失败: {e}")
                        continue
                else:
                    # 即使跳过检测，也要推送视频流（使用原始帧，不进行检测）
                    # 这样可以保证视频流的实时性
                    if (
                        self.video_stream_service
                        and self.frame_count % self.config.stream_interval == 0
                    ):
                        try:
                            logger.info(
                                f"跳过检测但推送视频流: camera={self.config.camera_id}, "
                                f"frame={self.frame_count}, interval={self.config.stream_interval}"
                            )
                            success = await self.video_stream_service.push_frame(
                                camera_id=self.config.camera_id,
                                frame=frame,  # 使用原始帧，不进行检测
                                quality=self.config.video_quality,
                                target_width=self.config.stream_width,
                                target_height=self.config.stream_height,
                            )
                            if success:
                                logger.info(
                                    f"视频流推送成功（跳过检测模式）: camera={self.config.camera_id}, frame={self.frame_count}"
                                )
                            else:
                                logger.warning(
                                    f"视频流推送失败（跳过检测模式）: camera={self.config.camera_id}, frame={self.frame_count}"
                                )
                        except Exception as e:
                            logger.error(
                                f"推送视频流失败（跳过检测模式）: camera={self.config.camera_id}, frame={self.frame_count}, error={e}",
                                exc_info=True,
                            )

                # 更新统计
                self._update_statistics(self.frame_count)

            logger.info(
                f"检测循环结束: 总帧数={self.frame_count}, "
                f"处理数={self.process_count}, "
                f"运行时间={time.time() - self.start_time:.1f}s"
            )

        except Exception as e:
            logger.error(f"检测循环异常: {e}")
            raise

        finally:
            # 释放资源
            if cap is not None:
                self._release_video_source(cap)

    def stop(self):
        """停止检测循环"""
        logger.info("请求停止检测循环...")
        self.shutdown_requested = True


# 辅助函数：从命令行参数创建配置
def create_config_from_args(args) -> DetectionLoopConfig:
    """
    从命令行参数创建检测循环配置

    Args:
        args: 命令行参数

    Returns:
        DetectionLoopConfig对象
    """
    import os

    return DetectionLoopConfig(
        camera_id=getattr(args, "camera_id", "unknown"),
        source=args.source,
        log_interval=getattr(args, "log_interval", 1),
        stream_interval=int(os.getenv("VIDEO_STREAM_INTERVAL", "3")),
        video_quality=int(os.getenv("VIDEO_STREAM_QUALITY", "60")),
        stream_width=int(os.getenv("VIDEO_STREAM_WIDTH", "800")),
        stream_height=int(os.getenv("VIDEO_STREAM_HEIGHT", "450")),
    )
