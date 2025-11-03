#!/usr/bin/env python
"""配置验证脚本."""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """验证配置."""
    try:
        from src.config.env_config import Config

        config = Config()
        config.validate()

        print("=" * 60)
        print("✅ 配置验证通过")
        print("=" * 60)
        print(f"   环境: {config.environment}")
        print(f"   日志级别: {config.log_level}")

        # 显示数据库配置（隐藏密码）
        db_url = config.database_url
        if "@" in db_url:
            db_info = db_url.split("@")[1]
            print(f"   数据库: ***@{db_info}")
        else:
            print(f"   数据库: 未配置")

        # 显示Redis配置（隐藏密码）
        redis_url = config.redis_url
        if "@" in redis_url:
            redis_info = redis_url.split("@")[1]
            print(f"   Redis: ***@{redis_info}")
        else:
            print(f"   Redis: 未配置")

        print(f"   领域服务: {'启用' if config.use_domain_service else '禁用'}")
        print(f"   灰度百分比: {config.rollout_percent}%")
        print(f"   API端口: {config.api_port}")
        print("=" * 60)

        return 0

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("   提示: 请确保在项目根目录运行此脚本")
        return 1
    except ValueError as e:
        print("=" * 60)
        print(f"❌ 配置验证失败")
        print("=" * 60)
        print(f"   错误: {e}")
        print("")
        print("建议:")
        print("   1. 检查.env文件是否存在")
        print("   2. 确保必需的配置项已设置")
        print("   3. 参考.env.example文件")
        print("=" * 60)
        return 1
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
