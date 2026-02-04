"""日志节流器和环境感知配置单元测试."""

import logging
import os
from unittest.mock import patch

from src.utils.logger import LogThrottler, get_log_level_from_env, get_throttler


class TestLogThrottler:
    """测试LogThrottler类."""

    def test_basic_throttling(self):
        """测试基本的节流功能."""
        throttler = LogThrottler(interval=3)

        # 第1次：不记录
        should_log, count = throttler.should_log("test_key")
        assert should_log is False
        assert count == 1

        # 第2次：不记录
        should_log, count = throttler.should_log("test_key")
        assert should_log is False
        assert count == 2

        # 第3次：记录（interval=3）
        should_log, count = throttler.should_log("test_key")
        assert should_log is True
        assert count == 3

        # 第4次：不记录
        should_log, count = throttler.should_log("test_key")
        assert should_log is False
        assert count == 4

        # 第6次：记录
        throttler.should_log("test_key")  # 5
        should_log, count = throttler.should_log("test_key")  # 6
        assert should_log is True
        assert count == 6

    def test_multiple_keys(self):
        """测试多个key的独立计数."""
        throttler = LogThrottler(interval=2)

        # key1: 第1次
        should_log, count = throttler.should_log("key1")
        assert should_log is False
        assert count == 1

        # key2: 第1次
        should_log, count = throttler.should_log("key2")
        assert should_log is False
        assert count == 1

        # key1: 第2次（应该记录）
        should_log, count = throttler.should_log("key1")
        assert should_log is True
        assert count == 2

        # key2: 第2次（应该记录）
        should_log, count = throttler.should_log("key2")
        assert should_log is True
        assert count == 2

    def test_reset(self):
        """测试重置计数器."""
        throttler = LogThrottler(interval=3)

        # 累积计数
        throttler.should_log("test_key")  # 1
        throttler.should_log("test_key")  # 2

        # 重置
        throttler.reset("test_key")

        # 计数从头开始
        should_log, count = throttler.should_log("test_key")
        assert should_log is False
        assert count == 1

    def test_reset_all(self):
        """测试重置所有计数器."""
        throttler = LogThrottler(interval=2)

        throttler.should_log("key1")
        throttler.should_log("key2")
        throttler.should_log("key3")

        throttler.reset_all()

        # 所有key的计数都应该重置
        should_log, count = throttler.should_log("key1")
        assert count == 1
        should_log, count = throttler.should_log("key2")
        assert count == 1
        should_log, count = throttler.should_log("key3")
        assert count == 1

    def test_max_keys_limit(self):
        """测试最大key数量限制."""
        throttler = LogThrottler(interval=2, max_keys=3)

        # 添加3个key（达到最大值）
        throttler.should_log("key1")
        throttler.should_log("key2")
        throttler.should_log("key3")

        assert len(throttler.counters) == 3

        # 添加第4个key（应该删除最不活跃的key）
        throttler.should_log("key4")
        assert len(throttler.counters) == 3
        assert "key4" in throttler.counters

    def test_high_frequency_scenario(self):
        """测试高频场景（模拟30fps视频）."""
        throttler = LogThrottler(interval=30)
        log_count = 0

        # 模拟100帧
        for i in range(100):
            should_log, count = throttler.should_log("video_frames")
            if should_log:
                log_count += 1

        # 100帧应该记录3次（30, 60, 90）
        assert log_count == 3

    def test_interval_one(self):
        """测试interval=1（每次都记录）."""
        throttler = LogThrottler(interval=1)

        for i in range(10):
            should_log, count = throttler.should_log("test")
            assert should_log is True
            assert count == i + 1

    def test_large_interval(self):
        """测试大interval值."""
        throttler = LogThrottler(interval=1000)

        # 前999次都不应该记录
        for i in range(999):
            should_log, count = throttler.should_log("test")
            assert should_log is False
            assert count == i + 1

        # 第1000次应该记录
        should_log, count = throttler.should_log("test")
        assert should_log is True
        assert count == 1000


class TestGetLogLevelFromEnv:
    """测试get_log_level_from_env函数."""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_level(self):
        """测试默认日志级别（无环境变量）."""
        level = get_log_level_from_env()
        # 无ENV环境变量时，默认是"development"，对应DEBUG级别
        assert level == logging.DEBUG

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"})
    def test_log_level_env_var(self):
        """测试LOG_LEVEL环境变量优先级最高."""
        level = get_log_level_from_env()
        assert level == logging.DEBUG

    @patch.dict(os.environ, {"LOG_LEVEL": "ERROR"})
    def test_log_level_error(self):
        """测试LOG_LEVEL=ERROR."""
        level = get_log_level_from_env()
        assert level == logging.ERROR

    @patch.dict(os.environ, {"LOG_LEVEL": "WARNING"})
    def test_log_level_warning(self):
        """测试LOG_LEVEL=WARNING."""
        level = get_log_level_from_env()
        assert level == logging.WARNING

    @patch.dict(os.environ, {"ENV": "production"})
    def test_production_env(self):
        """测试生产环境（ENV=production）."""
        level = get_log_level_from_env()
        assert level == logging.INFO

    @patch.dict(os.environ, {"ENV": "prod"})
    def test_prod_env_alias(self):
        """测试生产环境别名（ENV=prod）."""
        level = get_log_level_from_env()
        assert level == logging.INFO

    @patch.dict(os.environ, {"ENV": "development"})
    def test_development_env(self):
        """测试开发环境（ENV=development）."""
        level = get_log_level_from_env()
        assert level == logging.DEBUG

    @patch.dict(os.environ, {"ENV": "dev"})
    def test_dev_env_alias(self):
        """测试开发环境别名（ENV=dev）."""
        level = get_log_level_from_env()
        assert level == logging.DEBUG

    @patch.dict(os.environ, {"ENV": "testing"})
    def test_testing_env(self):
        """测试测试环境（ENV=testing）."""
        level = get_log_level_from_env()
        assert level == logging.WARNING

    @patch.dict(os.environ, {"ENV": "test"})
    def test_test_env_alias(self):
        """测试测试环境别名（ENV=test）."""
        level = get_log_level_from_env()
        assert level == logging.WARNING

    @patch.dict(os.environ, {"ENV": "production", "LOG_LEVEL": "DEBUG"})
    def test_log_level_overrides_env(self):
        """测试LOG_LEVEL优先于ENV."""
        level = get_log_level_from_env()
        assert level == logging.DEBUG  # LOG_LEVEL优先

    @patch.dict(os.environ, {"ENV": "unknown_env"})
    def test_unknown_env(self):
        """测试未知环境（应该使用默认INFO）."""
        level = get_log_level_from_env()
        assert level == logging.INFO

    @patch.dict(os.environ, {"LOG_LEVEL": "INVALID"})
    def test_invalid_log_level(self):
        """测试无效的LOG_LEVEL（应该忽略，使用ENV的默认值）."""
        level = get_log_level_from_env()
        # 无效的LOG_LEVEL会被忽略，使用ENV的默认值（development=DEBUG）
        assert level == logging.DEBUG

    @patch.dict(os.environ, {"LOG_LEVEL": "debug"})  # 小写
    def test_log_level_case_insensitive(self):
        """测试LOG_LEVEL大小写不敏感."""
        level = get_log_level_from_env()
        assert level == logging.DEBUG


class TestGetThrottler:
    """测试get_throttler函数."""

    def test_returns_throttler_instance(self):
        """测试返回LogThrottler实例."""
        throttler = get_throttler()
        assert isinstance(throttler, LogThrottler)

    def test_returns_same_instance(self):
        """测试返回同一个全局实例."""
        throttler1 = get_throttler()
        throttler2 = get_throttler()
        assert throttler1 is throttler2

    def test_global_throttler_works(self):
        """测试全局throttler正常工作."""
        throttler = get_throttler()
        throttler.reset_all()  # 清理之前的状态

        should_log, count = throttler.should_log("test_global")
        assert count == 1


class TestRealWorldScenarios:
    """测试真实使用场景."""

    def test_video_frame_logging(self):
        """测试视频帧日志场景（30fps）."""
        throttler = LogThrottler(interval=30)
        logs = []

        # 模拟5秒的视频（150帧）
        for frame_num in range(150):
            should_log, count = throttler.should_log("camera_001_frames")
            if should_log:
                logs.append(f"已推送 {count} 帧")

        # 应该记录5次（30, 60, 90, 120, 150）
        assert len(logs) == 5
        assert logs[0] == "已推送 30 帧"
        assert logs[-1] == "已推送 150 帧"

    def test_multiple_cameras(self):
        """测试多个摄像头独立计数."""
        throttler = LogThrottler(interval=10)

        # 摄像头1推送20帧
        for _ in range(20):
            throttler.should_log("camera_001")

        # 摄像头2推送15帧
        for _ in range(15):
            throttler.should_log("camera_002")

        # 检查计数
        should_log, count1 = throttler.should_log("camera_001")
        should_log, count2 = throttler.should_log("camera_002")

        assert count1 == 21  # 20 + 1
        assert count2 == 16  # 15 + 1

    @patch.dict(os.environ, {"ENV": "production"})
    def test_production_logging_setup(self):
        """测试生产环境日志配置."""
        level = get_log_level_from_env()
        assert level == logging.INFO

        # 在生产环境，DEBUG日志不应该输出
        logger = logging.getLogger("test_prod")
        logger.setLevel(level)

        assert logger.level == logging.INFO
        assert not logger.isEnabledFor(logging.DEBUG)
        assert logger.isEnabledFor(logging.INFO)
