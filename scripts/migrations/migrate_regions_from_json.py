#!/usr/bin/env python3
"""从JSON配置文件迁移区域数据到数据库.

使用方法:
    python scripts/migrate_regions_from_json.py [--json-path config/regions.json] [--dry-run]
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

try:
    from src.core.region import Region, RegionType
except ImportError:
    # 兼容导入
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.core.region import Region, RegionType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def migrate_regions(
    database_url: str,
    json_path: str,
    dry_run: bool = False,
):
    """从JSON文件迁移区域数据到数据库.

    Args:
        database_url: 数据库连接URL
        json_path: JSON配置文件路径
        dry_run: 是否为干运行（不实际写入数据库）
    """
    logger.info("=" * 80)
    logger.info("区域配置迁移工具")
    logger.info("=" * 80)
    logger.info(f"JSON文件: {json_path}")
    logger.info(f"数据库: {database_url}")
    logger.info(f"模式: {'干运行（预览）' if dry_run else '实际迁移'}")
    logger.info("")

    # 1. 读取JSON配置文件
    if not os.path.exists(json_path):
        logger.error(f"JSON文件不存在: {json_path}")
        sys.exit(1)

    logger.info("[步骤1/4] 读取JSON配置文件...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        regions_json = json_data.get("regions", [])
        meta_data = json_data.get("meta", {})
        logger.info(f"✓ 找到 {len(regions_json)} 个区域配置")
        logger.info(f"✓ 找到meta配置: {bool(meta_data)}")
    except Exception as e:
        logger.error(f"读取JSON文件失败: {e}")
        sys.exit(1)

    if not regions_json:
        logger.warning("JSON文件中没有区域配置，无需迁移")
        sys.exit(0)

    # 2. 解析并转换为Region实体
    logger.info("[步骤2/4] 解析区域配置...")
    regions = []
    for region_data in regions_json:
        try:
            region_id = region_data.get("region_id")
            if not region_id:
                logger.warning(f"跳过缺少ID的区域配置: {region_data.get('name', 'unknown')}")
                continue

            # 转换类型
            region_type_str = region_data.get("region_type", "entrance")
            try:
                region_type = RegionType(region_type_str)
            except ValueError:
                logger.warning(f"未知的区域类型: {region_type_str}，使用默认类型")
                region_type = RegionType.ENTRANCE

            # 转换polygon
            polygon_data = region_data.get("polygon", [])
            polygon = []
            for point in polygon_data:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    polygon.append((float(point[0]), float(point[1])))
                else:
                    logger.warning(f"无效的多边形点: {point}")
                    continue

            if not polygon:
                logger.warning(f"区域 {region_id} 没有有效的多边形点，跳过")
                continue

            # 创建Region实体
            region = Region(
                region_id=region_id,
                region_type=region_type,
                polygon=polygon,
                name=region_data.get("name", region_id),
            )
            region.is_active = region_data.get("is_active", True)

            # 复制rules
            if "rules" in region_data:
                region.rules.update(region_data["rules"])

            # 注意: stats不迁移，应该实时存储在数据库
            # 如果需要，可以单独存储stats到统计表

            regions.append(region)
            logger.info(f"  ✓ 解析区域: {region_id} ({region.name})")
        except Exception as e:
            logger.error(f"解析区域配置失败: {e}, data={region_data}")
            continue

    logger.info(f"✓ 成功解析 {len(regions)} 个区域")
    logger.info("")

    # 3. 连接数据库
    logger.info("[步骤3/4] 连接数据库...")
    if dry_run:
        logger.info("  ⚠️  干运行模式，跳过数据库连接")
    else:
        try:
            conn = await asyncpg.connect(database_url)
            logger.info("✓ 数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            sys.exit(1)

        # 确保regions表存在
        try:
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
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_regions_camera_id
                ON regions(camera_id) WHERE camera_id IS NOT NULL;
                CREATE INDEX IF NOT EXISTS idx_regions_type
                ON regions(region_type);
                CREATE INDEX IF NOT EXISTS idx_regions_active
                ON regions(is_active);
                """
            )
            logger.info("✓ regions表已确保存在")

            # 确保UUID扩展存在
            await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

            # 确保system_configs表存在（用于存储meta）
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS system_configs (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    config_key VARCHAR(100) UNIQUE NOT NULL,
                    config_value JSONB NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            logger.info("✓ system_configs表已确保存在")
        except Exception as e:
            logger.error(f"创建表失败: {e}")
            await conn.close()
            sys.exit(1)

    # 4. 迁移数据
    logger.info("[步骤4/4] 迁移数据到数据库...")
    if dry_run:
        logger.info("  ⚠️  干运行模式，预览迁移操作")
        for region in regions:
            logger.info(f"  → 将迁移: {region.region_id} ({region.name})")
        if meta_data:
            logger.info(f"  → 将迁移meta配置")
        logger.info("")
        logger.info("✓ 预览完成，使用 --no-dry-run 执行实际迁移")
        return

    migrated = 0
    errors = 0

    # 迁移区域
    for region in regions:
        try:
            # 检查是否已存在
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM regions WHERE region_id = $1)",
                region.region_id,
            )

            polygon_json = json.dumps([list(p) for p in region.polygon])
            rules_json = json.dumps(region.rules)

            if exists:
                # 更新现有记录
                await conn.execute(
                    """
                    UPDATE regions SET
                        region_type = $1,
                        name = $2,
                        polygon = $3,
                        is_active = $4,
                        rules = $5,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE region_id = $6
                    """,
                    region.region_type.value,
                    region.name,
                    polygon_json,
                    region.is_active,
                    rules_json,
                    region.region_id,
                )
                logger.info(f"  ✓ 更新: {region.region_id} ({region.name})")
                migrated += 1
            else:
                # 插入新记录
                await conn.execute(
                    """
                    INSERT INTO regions
                    (region_id, region_type, name, polygon, is_active, rules, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    region.region_id,
                    region.region_type.value,
                    region.name,
                    polygon_json,
                    region.is_active,
                    rules_json,
                )
                logger.info(f"  ✓ 插入: {region.region_id} ({region.name})")
                migrated += 1
        except Exception as e:
            logger.error(f"  ✗ 迁移失败: {region.region_id} - {e}")
            errors += 1

    # 迁移meta配置（如果有）
    if meta_data:
        try:
            await conn.execute(
                """
                INSERT INTO system_configs (config_key, config_value, description)
                VALUES ('regions_meta', $1, '区域meta配置')
                ON CONFLICT (config_key) DO UPDATE SET
                    config_value = EXCLUDED.config_value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                json.dumps(meta_data),
            )
            logger.info(f"  ✓ 迁移meta配置")
        except Exception as e:
            logger.warning(f"  ⚠️  迁移meta配置失败: {e}")

    await conn.close()

    # 5. 迁移总结
    logger.info("")
    logger.info("=" * 80)
    logger.info("迁移完成")
    logger.info("=" * 80)
    logger.info(f"总计: {len(regions)} 个区域")
    logger.info(f"成功: {migrated} 个")
    logger.info(f"失败: {errors} 个")
    if meta_data:
        logger.info(f"Meta配置: ✓ 已迁移")
    logger.info("")
    logger.info("✓ 区域配置已从JSON迁移到数据库")
    logger.info("  现在可以移除RegionService中的JSON写入逻辑")
    logger.info("  注意: stats统计信息应该实时存储在数据库，未迁移")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从JSON迁移区域配置到数据库")
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="干运行模式（不实际写入数据库）",
    )

    args = parser.parse_args()

    # 获取数据库URL
    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("请提供数据库URL: --database-url 或设置环境变量 DATABASE_URL")
        sys.exit(1)

    # 执行迁移
    asyncio.run(migrate_regions(database_url, args.json_path, args.dry_run))
