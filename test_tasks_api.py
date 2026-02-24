#!/usr/bin/env python3
"""测试任务API集成"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_health_check():
    """测试健康检查任务"""
    print("=== 测试健康检查任务 ===")
    
    try:
        response = requests.post(f"{BASE_URL}/tasks/health")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"任务ID: {data.get('task_id')}")
            print(f"任务状态: {data.get('status')}")
            print(f"结果: {data.get('result')}")
            return data.get('task_id')
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    return None

def test_create_video_task():
    """测试创建视频处理任务"""
    print("\n=== 测试创建视频处理任务 ===")
    
    try:
        payload = {
            "task_type": "video_processing",
            "parameters": {
                "video_path": "/path/to/test/video.mp4",
                "config": {
                    "model_name": "handwash_detector",
                    "confidence_threshold": 0.5,
                    "output_format": "json"
                }
            }
        }
        
        response = requests.post(f"{BASE_URL}/tasks", json=payload)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"任务ID: {data.get('task_id')}")
            print(f"任务类型: {data.get('task_type')}")
            print(f"任务状态: {data.get('status')}")
            return data.get('task_id')
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    return None

def test_get_task_status(task_id):
    """测试获取任务状态"""
    print(f"\n=== 测试获取任务状态: {task_id} ===")
    
    try:
        response = requests.get(f"{BASE_URL}/tasks/{task_id}")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"任务ID: {data.get('task_id')}")
            print(f"任务状态: {data.get('status')}")
            print(f"进度: {data.get('progress')}")
            print(f"错误: {data.get('error')}")
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")

def test_simplified_video_task():
    """测试简化视频处理任务接口"""
    print("\n=== 测试简化视频处理任务接口 ===")
    
    try:
        # 使用简化接口
        params = {
            "video_path": "/path/to/another/video.mp4"
        }
        
        response = requests.post(f"{BASE_URL}/tasks/video/process", params=params)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"任务ID: {data.get('task_id')}")
            print(f"任务类型: {data.get('task_type')}")
            print(f"任务状态: {data.get('status')}")
            return data.get('task_id')
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    return None

def test_list_tasks():
    """测试列出任务"""
    print("\n=== 测试列出任务 ===")
    
    try:
        response = requests.get(f"{BASE_URL}/tasks")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"总任务数: {data.get('total')}")
            print(f"当前页: {data.get('page')}")
            print(f"每页大小: {data.get('page_size')}")
            print(f"总页数: {data.get('total_pages')}")
            
            tasks = data.get('tasks', [])
            print(f"任务列表: {len(tasks)} 个任务")
            for i, task in enumerate(tasks[:3]):  # 只显示前3个
                print(f"  任务 {i+1}: {task.get('task_id')} - {task.get('task_type')} - {task.get('status')}")
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")

def test_batch_tasks():
    """测试批量任务"""
    print("\n=== 测试批量任务 ===")
    
    try:
        payload = {
            "tasks": [
                {
                    "task_type": "health_check",
                    "parameters": {}
                },
                {
                    "task_type": "video_processing",
                    "parameters": {
                        "video_path": "/path/to/video1.mp4"
                    }
                },
                {
                    "task_type": "video_processing",
                    "parameters": {
                        "video_path": "/path/to/video2.mp4"
                    }
                }
            ],
            "parallel": False
        }
        
        response = requests.post(f"{BASE_URL}/tasks/batch", json=payload)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"批量任务ID: {data.get('batch_id')}")
            print(f"总任务数: {data.get('total_tasks')}")
            print(f"成功任务数: {data.get('successful_tasks')}")
            print(f"失败任务数: {data.get('failed_tasks')}")
            
            tasks = data.get('tasks', [])
            for i, task in enumerate(tasks):
                print(f"  任务 {i+1}: {task.get('task_id')} - {task.get('status')}")
        else:
            print(f"错误: {response.text}")
    except Exception as e:
        print(f"请求失败: {e}")

def main():
    """主测试函数"""
    print("开始测试任务API集成...")
    
    # 测试健康检查任务
    health_task_id = test_health_check()
    
    # 测试创建视频处理任务
    video_task_id = test_create_video_task()
    
    # 测试简化接口
    simple_task_id = test_simplified_video_task()
    
    # 等待一下让任务有机会开始
    print("\n等待2秒让任务开始执行...")
    time.sleep(2)
    
    # 测试获取任务状态
    if health_task_id:
        test_get_task_status(health_task_id)
    
    if video_task_id:
        test_get_task_status(video_task_id)
    
    if simple_task_id:
        test_get_task_status(simple_task_id)
    
    # 测试列出任务
    test_list_tasks()
    
    # 测试批量任务
    test_batch_tasks()
    
    print("\n=== 所有测试完成 ===")

if __name__ == "__main__":
    main()