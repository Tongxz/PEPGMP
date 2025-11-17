#!/usr/bin/env python
"""测试MLOps API连接"""
import requests

BASE_URL = "http://localhost:8000/api/v1/mlops"

try:
    # 测试健康检查
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    print(f"✅ 健康检查: {response.status_code}")
    print(f"   响应: {response.json()}")
except requests.exceptions.ConnectionError:
    print("❌ 无法连接到API服务器")
    print("   请确保后端服务正在运行: python -m src.api.app")
    exit(1)
except Exception as e:
    print(f"❌ 连接失败: {e}")
    exit(1)

