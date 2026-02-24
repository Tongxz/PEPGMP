#!/usr/bin/env python3
"""测试Celery配置和连接"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.worker.celery_app import celery_app
from src.config.env_config import config

def test_celery_config():
    """测试Celery配置"""
    print("=== 测试Celery配置 ===")
    
    # 检查配置
    print(f"1. Redis URL: {celery_app.conf.broker_url}")
    print(f"2. Result backend: {celery_app.conf.result_backend}")
    print(f"3. Timezone: {celery_app.conf.timezone}")
    print(f"4. Task time limit: {celery_app.conf.task_time_limit}秒")
    
    # 测试Redis连接
    try:
        # 尝试创建Redis连接
        import redis
        redis_client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            decode_responses=True
        )
        response = redis_client.ping()
        print(f"5. Redis连接测试: {'成功' if response else '失败'}")
    except Exception as e:
        print(f"5. Redis连接测试失败: {e}")
    
    # 测试任务发现
    print("\n=== 测试任务发现 ===")
    try:
        registered_tasks = celery_app.tasks.keys()
        print(f"已注册的任务数量: {len(registered_tasks)}")
        for task_name in registered_tasks:
            print(f"  - {task_name}")
    except Exception as e:
        print(f"任务发现失败: {e}")

if __name__ == "__main__":
    test_celery_config()