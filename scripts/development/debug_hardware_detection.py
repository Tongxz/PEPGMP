#!/usr/bin/env python3
"""
调试硬件探测和配置选择
"""

import sys
from pathlib import Path

try:
    from src.utils.hardware_probe import decide_policy, detect_environment
except ImportError:
    # This is a workaround for running scripts directly from the repository root.
    # It adds the 'src' directory to the Python path.
    src_path = Path(__file__).resolve().parent.parent / "src"
    sys.path.insert(0, str(src_path))
    from src.utils.hardware_probe import decide_policy, detect_environment


def main():
    print("=" * 60)
    print("🔍 硬件探测调试信息")
    print("=" * 60)

    # 1. 硬件探测结果
    print("\n📊 硬件环境探测:")
    env = detect_environment()
    for key, value in env.items():
        print(f"  {key}: {value}")

    print("\n🎯 自动配置决策:")
    # 2. 模拟不同场景的配置
    scenarios = [
        ("默认场景", None, None, None),
        ("明确指定cuda", "cuda", None, None),
        ("指定cuda+imgsz", "cuda", 640, None),
    ]

    for name, device, imgsz, profile in scenarios:
        print(f"\n--- {name} ---")
        policy = decide_policy(
            preferred_profile=profile, user_device=device, user_imgsz=imgsz
        )

        for key, value in policy.items():
            if key == "env" and value:
                print(f"  {key}:")
                for env_key, env_value in value.items():
                    print(f"    {env_key} = {env_value}")
            else:
                print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("✅ 调试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
