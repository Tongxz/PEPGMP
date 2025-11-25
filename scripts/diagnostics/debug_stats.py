#!/usr/bin/env python3
"""
调试统计数据收集问题

检查：
1. 检测结果的实际结构
2. hairnet_results 和 handwash_results 的内容
3. 统计数据是否正确收集
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import json
import redis

def check_redis_stats(camera_id: str = "vid1"):
    """检查Redis中的统计数据"""
    try:
        redis_url = "redis://localhost:6379/0"
        r = redis.from_url(redis_url, decode_responses=True)
        
        # 从Redis缓存中获取最新统计数据
        # 注意：这里需要从CAMERA_STATS_CACHE中读取，但我们直接检查Redis channel的最后一个消息
        # 或者我们可以订阅channel来查看
        
        print(f"检查摄像头 {camera_id} 的统计数据...")
        print("=" * 60)
        
        # 尝试订阅最新的消息（非阻塞）
        pubsub = r.pubsub()
        pubsub.subscribe("hbd:stats")
        
        # 获取最新的消息
        messages = []
        for i in range(5):  # 最多读取5条消息
            message = pubsub.get_message(timeout=1)
            if message and message.get("type") == "message":
                try:
                    data = json.loads(message["data"])
                    if data.get("camera_id") == camera_id:
                        messages.append(data)
                except:
                    pass
        
        pubsub.close()
        
        if messages:
            latest = messages[-1]
            print("最新统计数据:")
            print(json.dumps(latest, indent=2, ensure_ascii=False))
            print("=" * 60)
            
            data = latest.get("data", {})
            print(f"detected_persons: {data.get('detected_persons', 0)}")
            print(f"detected_hairnets: {data.get('detected_hairnets', 0)}")
            print(f"detected_handwash: {data.get('detected_handwash', 0)}")
            print(f"processed_frames: {data.get('processed_frames', 0)}")
        else:
            print("未找到统计数据，可能检测进程未运行或未发布数据")
            
    except Exception as e:
        print(f"检查Redis失败: {e}")

if __name__ == "__main__":
    camera_id = sys.argv[1] if len(sys.argv) > 1 else "vid1"
    check_redis_stats(camera_id)

