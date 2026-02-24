#!/usr/bin/env python3
"""
区域数据审计脚本
用于检查regions表的polygon字段数据完整性

使用方法:
    python -m scripts.migrations.audit_region_data
"""

import asyncio
import logging
from typing import Dict

import asyncpg

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def audit_region_data(database_url: str) -> Dict:
    """审计区域数据并返回统计信息."""
    logger.info("=" * 80)
    logger.info("区域数据审计开始")
    logger.info("=" * 80)

    # 连接数据库
    conn = await asyncpg.connect(database_url)
    try:
        # 1. 检查表是否存在
        table_exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'regions'
            )
            """
        )

        if not table_exists:
            logger.warning("⚠️  regions表不存在")
            return {"error": "regions表不存在"}

        # 2. 统计总体情况
        logger.info("\n【1. 总体统计】")
        stats = await conn.fetchrow(
            """
            SELECT
                COUNT(*) as total_regions,
                COUNT(*) FILTER (WHERE polygon IS NULL) as null_polygon,
                COUNT(*) FILTER (WHERE jsonb_typeof(polygon) != 'array') as invalid_type,
                COUNT(*) FILTER (WHERE jsonb_typeof(polygon) = 'array'
                                AND jsonb_array_length(polygon) < 3) as insufficient_points,
                COUNT(*) FILTER (WHERE polygon IS NOT NULL
                                AND jsonb_typeof(polygon) = 'array'
                                AND jsonb_array_length(polygon) >= 3) as valid_regions
            FROM regions
            """
        )

        logger.info(f"  总区域数: {stats['total_regions']}")
        logger.info(f"  ✅ 有效区域: {stats['valid_regions']}")
        logger.info(f"  ❌ NULL polygon: {stats['null_polygon']}")
        logger.info(f"  ❌ 类型错误: {stats['invalid_type']}")
        logger.info(f"  ❌ 点数不足: {stats['insufficient_points']}")

        total_invalid = (
            stats["null_polygon"] + stats["invalid_type"] + stats["insufficient_points"]
        )
        logger.info(f"  ⚠️  异常数据总计: {total_invalid}")

        # 3. 列出异常数据详情
        if total_invalid > 0:
            logger.info("\n【2. 异常数据详情（前10条）】")
            invalid_regions = await conn.fetch(
                """
                SELECT
                    region_id,
                    name,
                    region_type,
                    camera_id,
                    CASE
                        WHEN polygon IS NULL THEN 'NULL'
                        WHEN jsonb_typeof(polygon) != 'array' THEN 'INVALID_TYPE'
                        WHEN jsonb_array_length(polygon) < 3 THEN 'INSUFFICIENT_POINTS'
                        ELSE 'UNKNOWN'
                    END as issue,
                    CASE
                        WHEN polygon IS NULL THEN NULL
                        WHEN jsonb_typeof(polygon) = 'array' THEN jsonb_array_length(polygon)
                        ELSE NULL
                    END as point_count,
                    is_active
                FROM regions
                WHERE polygon IS NULL
                   OR jsonb_typeof(polygon) != 'array'
                   OR jsonb_array_length(polygon) < 3
                ORDER BY camera_id, region_id
                LIMIT 10
                """
            )

            for region in invalid_regions:
                logger.info(
                    f"  - {region['region_id']} ({region['name']}): "
                    f"{region['issue']} | camera_id={region['camera_id']} | "
                    f"point_count={region['point_count']} | active={region['is_active']}"
                )

            # 4. 按camera_id统计
            logger.info("\n【3. 按摄像头统计异常区域】")
            camera_stats = await conn.fetch(
                """
                SELECT
                    camera_id,
                    COUNT(*) as total_regions,
                    COUNT(*) FILTER (WHERE polygon IS NULL
                                    OR jsonb_typeof(polygon) != 'array'
                                    OR jsonb_array_length(polygon) < 3) as invalid_regions
                FROM regions
                GROUP BY camera_id
                HAVING COUNT(*) FILTER (WHERE polygon IS NULL
                                       OR jsonb_typeof(polygon) != 'array'
                                       OR jsonb_array_length(polygon) < 3) > 0
                ORDER BY invalid_regions DESC
                """
            )

            for cam in camera_stats:
                logger.info(
                    f"  - camera_id={cam['camera_id']}: "
                    f"{cam['invalid_regions']}/{cam['total_regions']} 异常"
                )

        # 5. 检查是否有约束
        logger.info("\n【4. 数据库约束检查】")
        constraints = await conn.fetch(
            """
            SELECT
                conname as constraint_name,
                contype as constraint_type,
                pg_get_constraintdef(oid) as definition
            FROM pg_constraint
            WHERE conrelid = 'regions'::regclass
            ORDER BY conname
            """
        )

        if constraints:
            for constraint in constraints:
                logger.info(
                    f"  ✓ {constraint['constraint_name']}: {constraint['constraint_type']}"
                )
        else:
            logger.info("  ⚠️  未发现polygon相关约束")

        # 6. 返回结果
        result = {
            "total_regions": stats["total_regions"],
            "valid_regions": stats["valid_regions"],
            "invalid_regions": total_invalid,
            "null_polygon": stats["null_polygon"],
            "invalid_type": stats["invalid_type"],
            "insufficient_points": stats["insufficient_points"],
            "has_constraints": len(constraints) > 0,
        }

        logger.info("\n" + "=" * 80)
        if total_invalid == 0:
            logger.info("✅ 数据完整性检查通过！所有区域数据正常。")
        else:
            logger.info(f"⚠️  发现 {total_invalid} 条异常数据，需要修复。")
            logger.info("\n建议操作：")
            logger.info(
                "  1. 运行修复脚本: psql -f scripts/migrations/001_audit_and_fix_region_points.sql"
            )
            logger.info("  2. 或使用方案B手动修复（设置默认矩形，标记为需要重新配置）")
            logger.info("  3. 修复后重新运行此审计脚本验证")
        logger.info("=" * 80)

        return result

    finally:
        await conn.close()


async def main():
    """主函数."""
    # 从环境变量获取数据库URL
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://pepgmp_dev:pepgmp_dev_password@localhost:5432/pepgmp_development",
    )

    if len(sys.argv) > 1:
        database_url = sys.argv[1]

    logger.info(
        f"数据库URL: {database_url.split('@')[1] if '@' in database_url else database_url}"
    )

    try:
        result = await audit_region_data(database_url)
        sys.exit(0 if result.get("invalid_regions", 0) == 0 else 1)
    except Exception as e:
        logger.error(f"审计失败: {e}", exc_info=True)
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
