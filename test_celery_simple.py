#!/usr/bin/env python3
"""简单测试Celery任务"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.worker.tasks import health_check, process_video

def test_simple():
    """简单测试"""
    print("=== 简单测试Celery任务 ===")
    
    # 测试健康检查
    print("\n1. 测试健康检查任务...")
    try:
        result = health_check.delay()
        print(f"   任务ID: {result.id}")
        print(f"   任务状态: {result.status}")
        
        # 等待结果
        if result.ready():
            task_result = result.get(timeout=5)
            print(f"   结果: {task_result}")
        else:
            print("   任务未完成，等待...")
            task_result = result.get(timeout=10)
            print(f"   结果: {task_result}")
    except Exception as e:
        print(f"   失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试视频处理
    print("\n2. 测试视频处理任务...")
    try:
        result = process_video.delay('/path/to/test/video.mp4')
        print(f"   任务ID: {result.id}")
        print(f"   任务状态: {result.status}")
        
        # 等待结果
        if result.ready():
            task_result = result.get(timeout=5)
            print(f"   结果状态: {task_result.get('status')}")
        else:
            print("   任务未完成，等待...")
            task_result = result.get(timeout=15)
            print(f"   结果状态: {task_result.get('status')}")
            print(f"   检测数量: {len(task_result.get('detections', []))}")
    except Exception as e:
        print(f"   失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_simple()