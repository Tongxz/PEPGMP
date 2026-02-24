#!/usr/bin/env python3
"""完整测试Celery配置和任务"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.worker.celery_app import celery_app
from src.config.env_config import config

def test_celery_full():
    """完整测试Celery"""
    print("=== 完整测试Celery配置 ===")
    
    # 检查配置
    print(f"1. Redis URL: {celery_app.conf.broker_url}")
    print(f"2. Result backend: {celery_app.conf.result_backend}")
    print(f"3. Timezone: {celery_app.conf.timezone}")
    
    # 测试Redis连接
    try:
        import redis
        redis_client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            decode_responses=True
        )
        response = redis_client.ping()
        print(f"4. Redis连接测试: {'成功' if response else '失败'}")
    except Exception as e:
        print(f"4. Redis连接测试失败: {e}")
    
    # 测试任务注册
    print("\n=== 测试任务注册 ===")
    try:
        # 手动导入任务模块
        import importlib
        import src.worker.tasks
        
        # 重新加载模块
        importlib.reload(src.worker.tasks)
        
        # 检查任务是否在Celery应用中
        registered_tasks = list(celery_app.tasks.keys())
        custom_tasks = [t for t in registered_tasks if 'src.worker' in t]
        
        print(f"总任务数量: {len(registered_tasks)}")
        print(f"自定义任务数量: {len(custom_tasks)}")
        
        if custom_tasks:
            print("自定义任务:")
            for task_name in custom_tasks:
                print(f"  - {task_name}")
        else:
            print("警告: 未找到自定义任务!")
            
            # 尝试直接调用autodiscover
            print("\n尝试手动autodiscover...")
            celery_app.autodiscover_tasks(['src.worker.tasks'], force=True)
            
            # 再次检查
            registered_tasks = list(celery_app.tasks.keys())
            custom_tasks = [t for t in registered_tasks if 'src.worker' in t]
            print(f"手动发现后自定义任务数量: {len(custom_tasks)}")
            
    except Exception as e:
        print(f"任务注册测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试任务执行
    print("\n=== 测试任务执行 ===")
    try:
        # 导入任务函数
        from src.worker.tasks import health_check
        
        # 同步执行任务（用于测试）
        print("同步执行健康检查任务...")
        result = health_check.apply()
        
        # 等待结果
        if result.ready():
            task_result = result.get(timeout=5)
            print(f"任务执行结果: {task_result}")
        else:
            print("任务未完成")
            
    except Exception as e:
        print(f"任务执行测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_celery_full()