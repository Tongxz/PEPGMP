#!/usr/bin/env python3
"""性能测试：测量Celery任务性能"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import statistics
from src.worker.tasks import health_check, process_video

def measure_latency(task_func, *args, **kwargs):
    """测量单个任务延迟"""
    start_time = time.perf_counter()
    result = task_func(*args, **kwargs)
    end_time = time.perf_counter()
    
    # 等待任务完成
    task_result = result.get(timeout=10)
    
    latency = end_time - start_time
    return latency, task_result

def measure_throughput(task_func, num_tasks=10, *args, **kwargs):
    """测量吞吐量（任务/秒）"""
    start_time = time.perf_counter()
    
    results = []
    for i in range(num_tasks):
        result = task_func(*args, **kwargs)
        results.append(result)
    
    # 等待所有任务完成
    for result in results:
        result.get(timeout=10)
    
    end_time = time.perf_counter()
    total_time = end_time - start_time
    throughput = num_tasks / total_time
    
    return throughput, total_time

def main():
    """主性能测试函数"""
    print("=== Celery任务性能测试 ===")
    
    # 设置环境变量，使任务在eager模式下运行
    os.environ['CELERY_TASK_ALWAYS_EAGER'] = 'True'
    
    print("\n1. 健康检查任务延迟测试...")
    latencies = []
    for i in range(5):
        latency, result = measure_latency(health_check.delay)
        latencies.append(latency)
        print(f"   第{i+1}次: {latency:.4f} 秒")
    
    avg_latency = statistics.mean(latencies)
    std_latency = statistics.stdev(latencies) if len(latencies) > 1 else 0
    print(f"   平均延迟: {avg_latency:.4f} 秒")
    print(f"   标准差: {std_latency:.4f} 秒")
    
    print("\n2. 健康检查任务吞吐量测试...")
    throughput, total_time = measure_throughput(health_check.delay, num_tasks=20)
    print(f"   总时间: {total_time:.4f} 秒")
    print(f"   吞吐量: {throughput:.2f} 任务/秒")
    
    print("\n3. 视频处理任务延迟测试（模拟）...")
    # 使用模拟视频路径
    latencies = []
    for i in range(3):
        latency, result = measure_latency(process_video.delay, '/test/video.mp4')
        latencies.append(latency)
        print(f"   第{i+1}次: {latency:.4f} 秒")
    
    if latencies:
        avg_latency = statistics.mean(latencies)
        print(f"   平均延迟: {avg_latency:.4f} 秒")
    
    print("\n4. 并发任务测试...")
    start_time = time.perf_counter()
    
    # 创建10个并发任务
    results = []
    for i in range(10):
        result = health_check.delay()
        results.append(result)
    
    # 等待所有任务完成
    for result in results:
        result.get(timeout=10)
    
    end_time = time.perf_counter()
    concurrent_time = end_time - start_time
    print(f"   10个并发任务总时间: {concurrent_time:.4f} 秒")
    print(f"   平均每个任务: {concurrent_time/10:.4f} 秒")
    
    print("\n=== 性能测试总结 ===")
    print(f"健康检查任务:")
    print(f"  - 平均延迟: {statistics.mean(latencies[:5]):.4f} 秒")
    print(f"  - 吞吐量: {throughput:.2f} 任务/秒")
    print(f"  - 并发处理能力: {10/concurrent_time:.2f} 任务/秒")
    
    # 性能基准
    print(f"\n性能基准:")
    if avg_latency < 0.1:
        print(f"  ✅ 延迟优秀 (< 100ms)")
    elif avg_latency < 0.5:
        print(f"  ⚠️  延迟可接受 (< 500ms)")
    else:
        print(f"  ❌ 延迟较高 (> 500ms)")
    
    if throughput > 50:
        print(f"  ✅ 吞吐量优秀 (> 50 任务/秒)")
    elif throughput > 10:
        print(f"  ⚠️  吞吐量可接受 (> 10 任务/秒)")
    else:
        print(f"  ❌ 吞吐量较低 (< 10 任务/秒)")
    
    print("\n注意：此测试在eager模式下运行，仅用于基准测试。")
    print("实际生产环境性能可能受Redis、网络和worker数量影响。")

if __name__ == "__main__":
    main()