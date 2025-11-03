#!/usr/bin/env python3
"""从数据库导出相机数据到YAML配置文件（用于备份）.

使用方法:
    python scripts/export_cameras_to_yaml.py [--yaml-path config/cameras.yaml] [--database-url ...]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import asyncpg
import yaml

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def export_cameras(
    database_url: str,
    yaml_path: str,
):
    """从数据库导出相机数据到YAML文件.

    Args:
        database_url: 数据库连接URL
        yaml_path: YAML配置文件路径
    """
    logger.info("=" * 80)
    logger.info("相机配置导出工具（从数据库导出到YAML）")
    logger.info("=" * 80)
    logger.info(f"数据库: {database_url}")
    logger.info(f"YAML文件: {yaml_path}")
    logger.info("")

    # 1. 连接数据库
    logger.info("[步骤1/3] 连接数据库...")
    try:
        conn = await asyncpg.connect(database_url)
        logger.info("✓ 数据库连接成功")
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        sys.exit(1)

    # 2. 从数据库读取所有相机
    logger.info("[步骤2/3] 从数据库读取相机配置...")
    try:
        # 确保表存在
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cameras (
                id VARCHAR(100) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                location VARCHAR(200),
                status VARCHAR(20) DEFAULT 'inactive',
                camera_type VARCHAR(50) DEFAULT 'fixed',
                resolution JSONB,
                fps INTEGER,
                region_id VARCHAR(100),
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        rows = await conn.fetch(
            """
            SELECT id, name, location, status, camera_type, resolution, fps,
                   region_id, metadata, created_at, updated_at
            FROM cameras
            ORDER BY name
            """
        )

        cameras = []
        for row in rows:
            try:
                # 解析分辨率
                resolution = None
                if row["resolution"]:
                    if isinstance(row["resolution"], list):
                        resolution = row["resolution"]
                    elif isinstance(row["resolution"], str):
                        resolution = json.loads(row["resolution"])

                # 解析metadata
                metadata = row["metadata"] or {}
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)

                # 构建YAML格式的相机配置
                camera_dict = {
                    "id": row["id"],
                    "name": row["name"],
                    "location": row.get("location", "unknown"),
                    "status": row["status"],
                    "camera_type": row["camera_type"],
                }

                # 添加分辨率
                if resolution:
                    camera_dict["resolution"] = resolution

                # 添加fps
                if row["fps"]:
                    camera_dict["fps"] = row["fps"]

                # 添加region_id
                if row["region_id"]:
                    camera_dict["region_id"] = row["region_id"]

                # 从metadata提取字段到顶层（YAML格式）
                if "source" in metadata:
                    camera_dict["source"] = metadata["source"]

                # 提取其他字段
                for key in [
                    "regions_file",
                    "profile",
                    "device",
                    "imgsz",
                    "auto_tune",
                    "auto_start",
                    "env",
                ]:
                    if key in metadata:
                        camera_dict[key] = metadata[key]

                # 添加active字段（兼容旧格式）
                camera_dict["active"] = row["status"] == "active"

                cameras.append(camera_dict)
                logger.info(f"  ✓ 导出相机: {row['id']} ({row['name']})")
            except Exception as e:
                logger.error(f"  ✗ 解析相机失败: {row['id']} - {e}")
                continue

        logger.info(f"✓ 成功读取 {len(cameras)} 个相机")
        await conn.close()
    except Exception as e:
        logger.error(f"从数据库读取相机失败: {e}")
        await conn.close()
        sys.exit(1)

    # 3. 写入YAML文件
    logger.info("[步骤3/3] 写入YAML文件...")
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(yaml_path), exist_ok=True)

        # 构建YAML数据
        yaml_data = {"cameras": cameras}

        # 原子写入
        import tempfile

        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", delete=False, dir=os.path.dirname(yaml_path)
        ) as tf:
            yaml.safe_dump(
                yaml_data,
                tf,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )
            tmp_name = tf.name

        os.replace(tmp_name, yaml_path)
        logger.info(f"✓ YAML文件已写入: {yaml_path}")
    except Exception as e:
        logger.error(f"写入YAML文件失败: {e}")
        sys.exit(1)

    # 4. 导出总结
    logger.info("")
    logger.info("=" * 80)
    logger.info("导出完成")
    logger.info("=" * 80)
    logger.info(f"总计: {len(cameras)} 个相机")
    logger.info(f"文件: {yaml_path}")
    logger.info("")
    logger.info("✓ 相机配置已从数据库导出到YAML")
    logger.info("  此文件可用于备份或版本控制")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从数据库导出相机配置到YAML")
    parser.add_argument(
        "--yaml-path",
        default="config/cameras.yaml",
        help="YAML配置文件路径 (默认: config/cameras.yaml)",
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
    asyncio.run(export_cameras(database_url, args.yaml_path))
