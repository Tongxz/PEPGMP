#!/usr/bin/env python3
"""集成测试：验证Celery和API集成"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
from src.worker.tasks import health_check, process_video
from src.worker.celery_app import celery_app
from celery.result import AsyncResult

def test_celery_integration():
    """测试Celery集成"""
    print("=== 集成测试：Celery任务执行 ===")
    
    # 测试1: 健康检查
    print("\n1. 测试健康检查任务...")
    try:
        result = health_check.delay()
        print(f"   任务ID: {result.id}")
        
        # 等待结果
        task_result = result.get(timeout=10)
        print(f"   结果: {task_result}")
        print(f"   ✅ 健康检查任务成功")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False
    
    # 测试2: 视频处理
    print("\n2. 测试视频处理任务...")
    try:
        result = process_video.delay('/test/video.mp4')
        print(f"   任务ID: {result.id}")
        
        # 等待结果
        task_result = result.get(timeout=15)
        print(f"   结果状态: {task_result.get('status')}")
        print(f"   检测数量: {len(task_result.get('detections', []))}")
        print(f"   ✅ 视频处理任务成功")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False
    
    # 测试3: 任务状态查询
    print("\n3. 测试任务状态查询...")
    try:
        # 创建一个新任务
        result = health_check.delay()
        task_id = result.id
        
        # 使用AsyncResult查询状态
        async_result = AsyncResult(task_id, app=celery_app)
        print(f"   任务ID: {task_id}")
        print(f"   任务状态: {async_result.status}")
        
        # 等待完成
        async_result.get(timeout=10)
        print(f"   完成状态: {async_result.status}")
        print(f"   结果: {async_result.result}")
        print(f"   ✅ 任务状态查询成功")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False
    
    # 测试4: 多个任务并发
    print("\n4. 测试多个任务并发...")
    try:
        task_ids = []
        for i in range(3):
            result = health_check.delay()
            task_ids.append(result.id)
            print(f"   创建任务 {i+1}: {result.id}")
        
        # 等待所有任务完成
        for i, task_id in enumerate(task_ids):
            async_result = AsyncResult(task_id, app=celery_app)
            async_result.get(timeout=10)
            print(f"   任务 {i+1} 完成: {async_result.status}")
        
        print(f"   ✅ 多个任务并发成功")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False
    
    print("\n=== 所有集成测试通过 ===")
    return True

def test_api_simulation():
    """模拟API调用测试"""
    print("\n=== 模拟API调用测试 ===")
    
    # 模拟创建任务
    print("\n1. 模拟创建任务...")
    try:
        from src.api.schemas.tasks import TaskCreateRequest, TaskType
        
        # 创建任务请求
        task_request = TaskCreateRequest(
            task_type=TaskType.HEALTH_CHECK,
            parameters={}
        )
        
        print(f"   任务类型: {task_request.task_type}")
        print(f"   参数: {task_request.parameters}")
        print(f"   ✅ 任务请求模型验证成功")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False
    
    # 模拟任务响应
    print("\n2. 模拟任务响应...")
    try:
        from src.api.schemas.tasks import TaskResponse, TaskStatus
        
        # 创建任务响应
        task_response = TaskResponse(
            task_id="test-task-123",
            task_type=TaskType.HEALTH_CHECK,
            status=TaskStatus.SUCCESS,
            created_at=time.time(),
            result={"status": "ok", "message": "test"}
        )
        
        print(f"   任务ID: {task_response.task_id}")
        print(f"   任务状态: {task_response.status}")
        print(f"   结果: {task_response.result}")
        print(f"   ✅ 任务响应模型验证成功")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return False
    
    print("\n=== API模拟测试通过 ===")
    return True

def main():
    """主测试函数"""
    print("开始集成测试...")
    
    # 测试Celery集成
    celery_ok = test_celery_integration()
    
    # 测试API模拟
    api_ok = test_api_simulation()
    
    # 总结
    print("\n" + "="*50)
    print("集成测试总结:")
    print(f"  Celery集成: {'✅ 通过' if celery_ok else '❌ 失败'}")
    print(f"  API模拟: {'✅ 通过' if api_ok else '❌ 失败'}")
    print(f"  总体: {'✅ 所有测试通过' if celery_ok and api_ok else '❌ 部分测试失败'}")
    print("="*50)
    
    return celery_ok and api_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)