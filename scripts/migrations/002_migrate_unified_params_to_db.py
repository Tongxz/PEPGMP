#!/usr/bin/env python3
"""从unified_params.yaml迁移检测参数到数据库.

使用方法:
    python scripts/migrations/002_migrate_unified_params_to_db.py [--dry-run]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import asyncpg
import yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_unified_params_yaml(yaml_path: str) -> Dict[str, Any]:
    """从YAML文件加载统一参数配置."""
    if not os.path.exists(yaml_path):
        logger.error(f"YAML文件不存在: {yaml_path}")
        sys.exit(1)

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data
    except Exception as e:
        logger.error(f"读取YAML文件失败: {e}")
        sys.exit(1)


def extract_config_items(config_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从YAML配置数据中提取配置项.

    Args:
        config_data: YAML配置数据

    Returns:
        配置项列表，每个项包含 camera_id, config_type, config_key, config_value
    """
    items = []

    # 定义配置类型映射
    config_type_mapping = {
        "human_detection": "human_detection",
        "hairnet_detection": "hairnet_detection",
        "behavior_recognition": "behavior_recognition",
        "pose_detection": "pose_detection",
        "detection_rules": "detection_rules",
        "system": "system",
    }

    # 处理每个配置类型
    for config_type_key, config_type in config_type_mapping.items():
        if config_type_key in config_data:
            config_dict = config_data[config_type_key]
            if isinstance(config_dict, dict):
                for key, value in config_dict.items():
                    items.append(
                        {
                            "camera_id": None,  # 全局默认值
                            "config_type": config_type,
                            "config_key": key,
                            "config_value": value,
                        }
                    )

    return items


async def migrate_unified_params(
    database_url: str,
    yaml_path: str,
    dry_run: bool = False,
):
    """从YAML文件迁移检测参数到数据库.

    Args:
        database_url: 数据库连接URL
        yaml_path: YAML配置文件路径
        dry_run: 是否为干运行（不实际写入数据库）
    """
    logger.info("=" * 80)
    logger.info("检测参数配置迁移工具")
    logger.info("=" * 80)
    logger.info(f"YAML文件: {yaml_path}")
    logger.info(f"数据库: {database_url}")
    logger.info(f"模式: {'干运行（预览）' if dry_run else '实际迁移'}")
    logger.info("")

    # 1. 读取YAML配置文件
    logger.info("[步骤1/4] 读取YAML配置文件...")
    yaml_data = load_unified_params_yaml(yaml_path)
    logger.info("✓ YAML文件读取成功")

    # 2. 提取配置项
    logger.info("[步骤2/4] 提取配置项...")
    config_items = extract_config_items(yaml_data)
    logger.info(f"✓ 找到 {len(config_items)} 个配置项")

    # 3. 连接数据库
    logger.info("[步骤3/4] 连接数据库...")
    try:
        conn = await asyncpg.connect(database_url)
        logger.info("✓ 数据库连接成功")
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        sys.exit(1)

    try:
        # 确保表存在
        logger.info("检查detection_configs表是否存在...")
        table_exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'detection_configs'
            )
            """
        )

        if not table_exists:
            logger.info("创建detection_configs表...")
            # 读取SQL文件
            sql_file = (
                project_root
                / "scripts"
                / "migrations"
                / "001_create_detection_configs_table.sql"
            )
            if sql_file.exists():
                with open(sql_file, "r", encoding="utf-8") as f:
                    sql = f.read()
                await conn.execute(sql)
                logger.info("✓ detection_configs表已创建")
            else:
                logger.error(f"SQL文件不存在: {sql_file}")
                sys.exit(1)
        else:
            logger.info("✓ detection_configs表已存在")

        # 4. 插入配置项
        if dry_run:
            logger.info("[步骤4/4] 干运行模式：预览将插入的配置项...")
            for item in config_items:
                logger.info(
                    f"  - {item['config_type']}.{item['config_key']} = {item['config_value']} "
                    f"(camera_id={item['camera_id']})"
                )
            logger.info("")
            logger.info("✓ 预览完成（未实际写入数据库）")
        else:
            logger.info("[步骤4/4] 插入配置项到数据库...")
            inserted_count = 0
            updated_count = 0
            skipped_count = 0

            for item in config_items:
                try:
                    # 检查配置项是否已存在
                    existing = await conn.fetchrow(
                        """
                        SELECT id FROM detection_configs
                        WHERE camera_id IS NULL
                        AND config_type = $1
                        AND config_key = $2
                        """,
                        item["config_type"],
                        item["config_key"],
                    )

                    if existing:
                        # 更新现有配置项
                        await conn.execute(
                            """
                            UPDATE detection_configs
                            SET config_value = $1, updated_at = CURRENT_TIMESTAMP
                            WHERE id = $2
                            """,
                            json.dumps(item["config_value"]),
                            existing["id"],
                        )
                        updated_count += 1
                        logger.debug(
                            f"  更新: {item['config_type']}.{item['config_key']} = {item['config_value']}"
                        )
                    else:
                        # 插入新配置项
                        await conn.execute(
                            """
                            INSERT INTO detection_configs (camera_id, config_type, config_key, config_value)
                            VALUES ($1, $2, $3, $4)
                            """,
                            item["camera_id"],
                            item["config_type"],
                            item["config_key"],
                            json.dumps(item["config_value"]),
                        )
                        inserted_count += 1
                        logger.debug(
                            f"  插入: {item['config_type']}.{item['config_key']} = {item['config_value']}"
                        )
                except Exception as e:
                    logger.warning(
                        f"处理配置项失败: {item['config_type']}.{item['config_key']}, 错误: {e}"
                    )
                    skipped_count += 1

            logger.info("")
            logger.info("=" * 80)
            logger.info("迁移完成")
            logger.info("=" * 80)
            logger.info(f"插入: {inserted_count} 个配置项")
            logger.info(f"更新: {updated_count} 个配置项")
            logger.info(f"跳过: {skipped_count} 个配置项")
            logger.info(f"总计: {len(config_items)} 个配置项")

    finally:
        await conn.close()


async def main():
    """主函数."""
    parser = argparse.ArgumentParser(description="从unified_params.yaml迁移检测参数到数据库")
    parser.add_argument(
        "--database-url",
        type=str,
        default=os.getenv(
            "DATABASE_URL",
            "postgresql://pyt_dev:pyt_dev_password@localhost:5432/pyt_development",
        ),
        help="数据库连接URL",
    )
    parser.add_argument(
        "--yaml-path",
        type=str,
        default=str(project_root / "config" / "unified_params.yaml"),
        help="YAML配置文件路径",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干运行模式（不实际写入数据库）",
    )

    args = parser.parse_args()

    await migrate_unified_params(
        database_url=args.database_url,
        yaml_path=args.yaml_path,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    asyncio.run(main())
