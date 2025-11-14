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

    def update_from_redis(self):
        """从Redis读取配置并更新"""
        import os

        import redis

        try:
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                return

            r = redis.from_url(redis_url)
            config_key = f"video_stream:config:{self.camera_id}"
            config_data = r.hgetall(config_key)

            if config_data:
                # 解码bytes为字符串
                config_data = {
                    k.decode(): v.decode() if isinstance(v, bytes) else v
                    for k, v in config_data.items()
                }

                if "stream_interval" in config_data:
                    self.stream_interval = int(config_data["stream_interval"])
                    logger.info(f"从Redis更新stream_interval: {self.stream_interval}")

                if "log_interval" in config_data:
                    self.log_interval = int(config_data["log_interval"])
                    logger.info(f"从Redis更新log_interval: {self.log_interval}")
        except Exception as e:
            logger.debug(f"从Redis读取配置失败（使用默认配置）: {e}")


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

        # 检测统计（用于发布到Redis）
        self.detection_stats = {
            "total_frames": 0,
            "processed_frames": 0,
            "detected_persons": 0,
            "detected_hairnets": 0,
            "detected_handwash": 0,
            "total_detection_time": 0.0,
        }
        self.last_stats_publish_time = None
        self.stats_publish_interval = 5.0  # 每5秒发布一次统计数据

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
        app_result = None

        # 更新检测统计（从检测结果中获取，不依赖app_result）
        self.detection_stats["processed_frames"] += 1

        # 统计人数（累计所有检测到的人数，不是取最大值）
        person_count = 0
        if hasattr(result, "person_detections"):
            person_count = (
                len(result.person_detections) if result.person_detections else 0
            )

        if person_count > 0:
            # 累计检测到的人数总数（所有帧的总和）
            self.detection_stats["detected_persons"] += person_count

        # 统计发网检测（从result中获取）
        # 注意：只统计实际检测到发网的人数（has_hairnet=True），不是所有检测结果
        hairnet_detected_count = 0
        hairnet_results_count = 0
        if hasattr(result, "hairnet_results") and result.hairnet_results:
            hairnet_results_count = len(result.hairnet_results)
            # 统计有发网的人数（has_hairnet=True）
            hairnet_detected_count = sum(
                1 for h in result.hairnet_results if h.get("has_hairnet") is True
            )
            # 累计有发网的人数
            self.detection_stats["detected_hairnets"] += hairnet_detected_count

        # 统计洗手检测
        # 注意：只统计实际检测到洗手的人数（is_handwashing=True），不是所有检测结果
        handwash_detected_count = 0
        handwash_results_count = 0
        if hasattr(result, "handwash_results") and result.handwash_results:
            handwash_results_count = len(result.handwash_results)
            # 统计正在洗手的人数（is_handwashing=True）
            handwash_detected_count = sum(
                1 for h in result.handwash_results if h.get("is_handwashing") is True
            )
            self.detection_stats["detected_handwash"] += handwash_detected_count

        # 每100帧记录一次统计信息（调试用）
        if self.detection_stats["processed_frames"] % 100 == 0:
            logger.info(
                f"统计更新: frame={frame_count}, person_count={person_count}, "
                f"total_persons={self.detection_stats['detected_persons']}, "
                f"hairnet_results={hairnet_results_count}, hairnet_detected={hairnet_detected_count}, "
                f"total_hairnets={self.detection_stats['detected_hairnets']}, "
                f"handwash_results={handwash_results_count}, handwash_detected={handwash_detected_count}, "
                f"total_handwash={self.detection_stats['detected_handwash']}"
            )
            # 调试：打印前几个检测结果的内容
            if (
                hasattr(result, "hairnet_results")
                and result.hairnet_results
                and len(result.hairnet_results) > 0
            ):
                logger.info(
                    f"发网检测结果示例 (前3个): {[{'has_hairnet': h.get('has_hairnet'), 'confidence': h.get('hairnet_confidence')} for h in result.hairnet_results[:3]]}"
                )
            if (
                hasattr(result, "handwash_results")
                and result.handwash_results
                and len(result.handwash_results) > 0
            ):
                logger.info(
                    f"洗手检测结果示例 (前3个): {[{'is_handwashing': h.get('is_handwashing'), 'confidence': h.get('handwash_confidence')} for h in result.handwash_results[:3]]}"
                )

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
                    logger.info(
                        f"✓ 帧 {frame_count}: 已保存 ({save_reason}), "
                        f"违规={app_result['result']['has_violations']}, "
                        f"严重程度={app_result['result']['violation_severity']:.2f}, "
                        f"detection_id={app_result.get('detection_id')}"
                    )

                # 累计处理时间（从app_result获取）
                if app_result:
                    processing_time = app_result.get("processing_time", 0.0)
                    self.detection_stats["total_detection_time"] += processing_time
            except Exception as e:
                logger.error(f"保存帧失败: {e}")

        # 3. 推送视频流（如果配置了视频流服务）
        # 视频流推送频率与检测频率保持一致，确保显示的是检测后的结果
        if self.video_stream_service and frame_count % self.config.log_interval == 0:
            try:
                # 判断是否有标注（使用annotated_image属性）
                annotated_frame = (
                    result.annotated_image
                    if hasattr(result, "annotated_image")
                    and result.annotated_image is not None
                    else None
                )
                has_annotations = annotated_frame is not None

                # 使用标注后的帧（如果有）或原始帧
                frame_to_push = annotated_frame if has_annotations else frame

                logger.info(
                    f"准备推送视频帧: camera={self.config.camera_id}, "
                    f"frame={frame_count}, detection_interval={self.config.log_interval}, "
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

    def _publish_stats_to_redis(self):
        """发布统计数据到Redis"""
        import json
        import os
        import time as time_module

        now = time_module.time()

        # 检查是否需要发布（每5秒或首次）
        if (
            self.last_stats_publish_time is None
            or now - self.last_stats_publish_time >= self.stats_publish_interval
        ):
            try:
                import redis

                # 获取Redis连接
                redis_url = os.getenv("REDIS_URL")
                if not redis_url:
                    host = os.getenv("REDIS_HOST", "localhost")
                    port = int(os.getenv("REDIS_PORT", "6379"))
                    db = int(os.getenv("REDIS_DB", "0"))
                    password = os.getenv("REDIS_PASSWORD")
                    redis_client = redis.Redis(
                        host=host,
                        port=port,
                        db=db,
                        password=password,
                        decode_responses=False,
                    )
                else:
                    redis_client = redis.from_url(redis_url, decode_responses=False)

                # 计算统计数据
                elapsed = (
                    time_module.time() - self.start_time if self.start_time else 1.0
                )
                # 修复FPS计算：使用总帧数和已处理帧数来计算
                if elapsed > 0:
                    # 使用实际处理帧数计算FPS（更准确）
                    avg_fps = self.detection_stats["processed_frames"] / elapsed
                else:
                    avg_fps = 0.0

                avg_detection_time = (
                    self.detection_stats["total_detection_time"]
                    / self.detection_stats["processed_frames"]
                    if self.detection_stats["processed_frames"] > 0
                    else 0.0
                )

                # 构建统计数据
                stats_data = {
                    "type": "stats",
                    "camera_id": self.config.camera_id,
                    "timestamp": now,
                    "data": {
                        "total_frames": self.frame_count,
                        "processed_frames": self.detection_stats["processed_frames"],
                        "detected_persons": self.detection_stats["detected_persons"],
                        "detected_hairnets": self.detection_stats["detected_hairnets"],
                        "detected_handwash": self.detection_stats["detected_handwash"],
                        "avg_fps": avg_fps,
                        "avg_detection_time": avg_detection_time,
                        "last_detection_time": now
                        if self.detection_stats["processed_frames"] > 0
                        else None,
                    },
                }

                # 发布到Redis
                payload = json.dumps(stats_data).encode("utf-8")
                redis_client.publish("hbd:stats", payload)

                self.last_stats_publish_time = now
                logger.info(
                    f"统计数据已发布到Redis: camera={self.config.camera_id}, "
                    f"total_frames={self.frame_count}, "
                    f"processed={self.detection_stats['processed_frames']}, "
                    f"detected_persons={self.detection_stats['detected_persons']}, "
                    f"detected_hairnets={self.detection_stats['detected_hairnets']}, "
                    f"detected_handwash={self.detection_stats['detected_handwash']}, "
                    f"avg_fps={avg_fps:.2f}, "
                    f"stats_data_keys={list(stats_data['data'].keys())}"
                )
                # 调试：打印实际发布的统计数据内容
                logger.debug(
                    f"发布的统计数据详情: {json.dumps(stats_data['data'], indent=2, ensure_ascii=False)}"
                )

            except Exception as e:
                logger.debug(f"发布统计数据到Redis失败: {e}")
                # 不中断流程，继续运行

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
            self.last_stats_publish_time = None
            # 重置检测统计（确保统计值被重置）
            self.detection_stats = {
                "total_frames": 0,
                "processed_frames": 0,
                "detected_persons": 0,
                "detected_hairnets": 0,
                "detected_handwash": 0,
                "total_detection_time": 0.0,
            }
            self.frame_count = 0
            self.process_count = 0
            logger.info(
                f"检测统计已重置: detected_persons={self.detection_stats['detected_persons']}, "
                f"detected_hairnets={self.detection_stats['detected_hairnets']}, "
                f"detected_handwash={self.detection_stats['detected_handwash']}"
            )

            # 启动时立即从Redis读取配置（不等待100帧）
            # 注意：Redis配置用于运行时动态更新，但不应覆盖命令行参数（初始化值）
            # 这里只用于同步，不强制覆盖已设置的命令行参数值
            initial_log_interval = self.config.log_interval  # 保存初始值（来自命令行参数或默认值）
            self.config.stream_interval

            # 从Redis读取配置
            redis_log_interval = None
            try:
                import os

                import redis

                redis_url = os.getenv("REDIS_URL")
                if redis_url:
                    r = redis.from_url(redis_url)
                    config_key = f"video_stream:config:{self.camera_id}"
                    config_data = r.hgetall(config_key)
                    if config_data:
                        config_data = {
                            k.decode(): v.decode() if isinstance(v, bytes) else v
                            for k, v in config_data.items()
                        }
                        if "log_interval" in config_data:
                            redis_log_interval = int(config_data["log_interval"])
            except Exception:
                pass

            # 更新配置（但保留初始值用于比较）
            self.config.update_from_redis()

            # 如果初始值（命令行参数）与Redis中的值不同，优先使用命令行参数
            # 这确保了用户通过相机配置设置的log_interval不会被Redis中的旧值覆盖
            if (
                redis_log_interval is not None
                and initial_log_interval != redis_log_interval
            ):
                logger.info(
                    f"检测到配置冲突：命令行参数 log_interval={initial_log_interval}，"
                    f"Redis中的值={redis_log_interval}，优先使用命令行参数"
                )
                self.config.log_interval = initial_log_interval
            elif redis_log_interval is not None:
                logger.info(
                    f"从Redis读取配置 log_interval={self.config.log_interval} " f"（与命令行参数一致）"
                )

            logger.info(
                f"开始视频处理循环: camera_id={self.config.camera_id}, "
                f"log_interval={self.config.log_interval}, "
                f"stream_interval={self.config.stream_interval}"
            )

            # 启动配置变更监听器
            try:
                from src.application.config_change_listener import ConfigChangeListener

                def on_config_change(notification: Dict[str, Any]):
                    """配置变更回调函数"""
                    config_type = notification.get("config_type")
                    config_key = notification.get("config_key")
                    config_value = notification.get("config_value")
                    change_type = notification.get("change_type", "update")

                    logger.info(
                        f"收到配置变更通知: config_type={config_type}, "
                        f"config_key={config_key}, change_type={change_type}, "
                        f"config_value={config_value}"
                    )

                    # 重新加载检测配置
                    try:
                        from src.core.config_reload_helper import (
                            reload_detection_config,
                        )

                        success = reload_detection_config(
                            detection_pipeline=self.detection_pipeline,
                            config_type=config_type,
                            config_key=config_key,
                            config_value=config_value,
                        )

                        if success:
                            logger.info(
                                f"配置已重新加载: config_type={config_type}, "
                                f"config_key={config_key}, config_value={config_value}"
                            )
                        else:
                            logger.warning(
                                f"配置重新加载失败: config_type={config_type}, "
                                f"config_key={config_key}"
                            )
                    except Exception as e:
                        logger.error(f"重新加载配置失败: {e}", exc_info=True)

                self.config_change_listener = ConfigChangeListener(
                    camera_id=self.config.camera_id,
                    on_config_change=on_config_change,
                )
                await self.config_change_listener.start()
                logger.info("配置变更监听器已启动")
            except Exception as e:
                logger.warning(f"启动配置变更监听器失败: {e}，将继续运行但不监听配置变更")

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

                # 定期从Redis读取配置更新（每100帧检查一次）
                # 注意：这是运行时动态更新，允许前端修改配置后实时生效
                if self.frame_count % 100 == 0:
                    old_log_interval = self.config.log_interval
                    self.config.update_from_redis()
                    if old_log_interval != self.config.log_interval:
                        logger.info(
                            f"从Redis更新log_interval: {old_log_interval} -> {self.config.log_interval}"
                        )

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
                    # 跳过检测时，不推送视频流
                    # 视频流只在检测时推送，确保显示的是检测后的结果
                    pass

                # 更新统计
                self._update_statistics(self.frame_count)

                # 发布统计数据到Redis（每5秒或每100帧）
                self._publish_stats_to_redis()

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
