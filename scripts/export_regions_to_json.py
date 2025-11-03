#!/usr/bin/env python3
"""从数据库导出区域数据到JSON配置文件（用于备份）.

使用方法:
    python scripts/export_regions_to_json.py [--json-path config/regions.json] [--database-url ...]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import asyncpg

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def export_regions(
    database_url: str,
    json_path: str,
):
    """从数据库导出区域数据到JSON文件.

    Args:
        database_url: 数据库连接URL
        json_path: JSON配置文件路径
    """
    logger.info("=" * 80)
    logger.info("区域配置导出工具（从数据库导出到JSON）")
    logger.info("=" * 80)
    logger.info(f"数据库: {database_url}")
    logger.info(f"JSON文件: {json_path}")
    logger.info("")

    # 1. 连接数据库
    logger.info("[步骤1/3] 连接数据库...")
    try:
        conn = await asyncpg.connect(database_url)
        logger.info("✓ 数据库连接成功")
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        sys.exit(1)

    # 2. 从数据库读取所有区域
    logger.info("[步骤2/3] 从数据库读取区域配置...")
    try:
        # 确保表存在
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS regions (
                region_id VARCHAR(100) PRIMARY KEY,
                region_type VARCHAR(50) NOT NULL,
                name VARCHAR(100) NOT NULL,
                polygon JSONB NOT NULL,
                is_active BOOLEAN DEFAULT true,
                rules JSONB DEFAULT '{}'::jsonb,
                camera_id VARCHAR(100),
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        rows = await conn.fetch(
            """
            SELECT region_id, region_type, name, polygon, is_active, rules, camera_id
            FROM regions
            ORDER BY name
            """
        )

        regions = []
        for row in rows:
            try:
                # 解析polygon
                polygon = row["polygon"]
                if isinstance(polygon, str):
                    polygon = json.loads(polygon)

                # 解析rules
                rules = row["rules"] or {}
                if isinstance(rules, str):
                    rules = json.loads(rules)

                # 构建JSON格式的区域配置
                region_dict = {
                    "region_id": row["region_id"],
                    "region_type": row["region_type"],
                    "name": row["name"],
                    "polygon": polygon,
                    "is_active": row["is_active"],
                    "rules": rules,
                }

                # 添加camera_id（如果存在）
                if row["camera_id"]:
                    region_dict["camera_id"] = row["camera_id"]

                regions.append(region_dict)
                logger.info(f"  ✓ 导出区域: {row['region_id']} ({row['name']})")
            except Exception as e:
                logger.error(f"  ✗ 解析区域失败: {row['region_id']} - {e}")
                continue

        logger.info(f"✓ 成功读取 {len(regions)} 个区域")

        # 读取meta配置
        meta_data = {}
        try:
            meta_row = await conn.fetchrow(
                """
                SELECT config_value FROM system_configs
                WHERE config_key = 'regions_meta'
                """
            )
            if meta_row:
                meta = meta_row["config_value"]
                if isinstance(meta, str):
                    meta_data = json.loads(meta)
                else:
                    meta_data = meta
                logger.info("✓ 成功读取meta配置")
        except Exception as e:
            logger.warning(f"读取meta配置失败: {e}，使用默认值")

        await conn.close()
    except Exception as e:
        logger.error(f"从数据库读取区域失败: {e}")
        await conn.close()
        sys.exit(1)

    # 3. 写入JSON文件
    logger.info("[步骤3/3] 写入JSON文件...")
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        # 构建JSON数据
        json_data = {"regions": regions}
        if meta_data:
            json_data["meta"] = meta_data

        # 原子写入
        import tempfile

        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", delete=False, dir=os.path.dirname(json_path)
        ) as tf:
            json.dump(json_data, tf, ensure_ascii=False, indent=2)
            tmp_name = tf.name

        os.replace(tmp_name, json_path)
        logger.info(f"✓ JSON文件已写入: {json_path}")
    except Exception as e:
        logger.error(f"写入JSON文件失败: {e}")
        sys.exit(1)

    # 4. 导出总结
    logger.info("")
    logger.info("=" * 80)
    logger.info("导出完成")
    logger.info("=" * 80)
    logger.info(f"总计: {len(regions)} 个区域")
    logger.info(f"文件: {json_path}")
    logger.info("")
    logger.info("✓ 区域配置已从数据库导出到JSON")
    logger.info("  此文件可用于备份或版本控制")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从数据库导出区域配置到JSON")
    parser.add_argument(
        "--json-path",
        default="config/regions.json",
        help="JSON配置文件路径 (默认: config/regions.json)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="数据库连接URL (默认: 从环境变量DATABASE_URL读取)",
    )

    args = parser.parse_args()

    # 获取数据库URL
    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("请提供数据库URL: --database-url 或设置环境变量 DATABASE_URL")
        sys.exit(1)

    # 执行导出
    asyncio.run(export_regions(database_url, args.json_path))
