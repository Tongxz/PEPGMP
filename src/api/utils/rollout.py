import os
import random
from typing import Optional


def should_use_domain(force_domain: Optional[bool] = None) -> bool:
    """
    计算本次请求是否走领域分支：
    - 若 force_domain 显式为 True，则强制走领域
    - 否则读取 USE_DOMAIN_SERVICE 环境变量（true/false）
    - 若 USE_DOMAIN_SERVICE=true 且设置了 ROLLOUT_PERCENT(0-100)，则按百分比灰度
    """
    if force_domain is True:
        return True

    use_env = os.getenv("USE_DOMAIN_SERVICE", "false").lower() == "true"
    if not use_env:
        return False

    # 百分比灰度
    try:
        percent = int(os.getenv("ROLLOUT_PERCENT", "100"))
    except Exception:
        percent = 100
    percent = max(0, min(100, percent))

    if percent >= 100:
        return True
    if percent <= 0:
        return False

    # 简单的随机采样
    return random.randint(1, 100) <= percent
