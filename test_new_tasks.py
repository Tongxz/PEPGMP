#!/usr/bin/env python3
"""测试新添加的Celery任务"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.worker.tasks import (
    health_check,
    process_video,
    run_detection_workflow,
    batch_process_videos,
    generate_dataset,
    train_model
)

def test_all_tasks():
    """测试所有任务"""
    print("=== 测试所有Celery任务 ===")
    
    # 测试健康检查
    print("\n1. 测试健康检查任务...")
    try:
        result = health_check.apply().get(timeout=5)
        print(f"   结果: {result}")
    except Exception as e:
        print(f"   失败: {e}")
    
    # 测试视频处理
    print("\n2. 测试视频处理任务...")
    try:
        result = process_video.apply(args=['/path/to/video.mp4']).get(timeout=10)
        print(f"   结果状态: {result.get('status')}")
        print(f"   检测数量: {len(result.get('detections', []))}")
    except Exception as e:
        print(f"   失败: {e}")
    
    # 测试工作流执行
    print("\n3. 测试工作流执行任务...")
    try:
        result = run_detection_workflow.apply(args=['workflow_001', {}]).get(timeout=10)
        print(f"   结果状态: {result.get('status')}")
        print(f"   步骤数量: {len(result.get('steps', []))}")
    except Exception as e:
        print(f"   失败: {e}")
    
    # 测试批量视频处理
    print("\n4. 测试批量视频处理任务...")
    try:
        videos = ['/path/to/video1.mp4', '/path/to/video2.mp4', '/path/to/video3.mp4']
        result = batch_process_videos.apply(args=[videos]).get(timeout=15)
        print(f"   总视频数: {result.get('total_videos')}")
        print(f"   成功数: {result.get('successful')}")
        print(f"   失败数: {result.get('failed')}")
    except Exception as e:
        print(f"   失败: {e}")
    
    # 测试数据集生成
    print("\n5. 测试数据集生成任务...")
    try:
        config = {'type': 'handwash', 'augmentation': True}
        result = generate_dataset.apply(args=[config, '/output/dataset']).get(timeout=15)
        print(f"   结果状态: {result.get('status')}")
        print(f"   总样本数: {result.get('statistics', {}).get('total_samples')}")
    except Exception as e:
        print(f"   失败: {e}")
    
    # 测试模型训练
    print("\n6. 测试模型训练任务...")
    try:
        config = {'epochs': 50, 'batch_size': 16}
        result = train_model.apply(args=[config, '/path/to/dataset']).get(timeout=20)
        print(f"   结果状态: {result.get('status')}")
        print(f"   模型名称: {result.get('model_info', {}).get('model_name')}")
        print(f"   准确率: {result.get('training_metrics', {}).get('precision')}")
    except Exception as e:
        print(f"   失败: {e}")
    
    print("\n=== 所有任务测试完成 ===")

if __name__ == "__main__":
    test_all_tasks()