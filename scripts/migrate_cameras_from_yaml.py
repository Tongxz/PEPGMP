#!/usr/bin/env python3
"""从YAML配置文件迁移相机数据到数据库.

使用方法:
    python scripts/migrate_cameras_from_yaml.py [--yaml-path config/cameras.yaml] [--dry-run]
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

from src.domain.entities.camera import Camera, CameraStatus, CameraType  # noqa: E402
from src.domain.value_objects.timestamp import Timestamp  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def migrate_cameras(
    database_url: str,
    yaml_path: str,
    dry_run: bool = False,
):
    """从YAML文件迁移相机数据到数据库.

    Args:
        database_url: 数据库连接URL
        yaml_path: YAML配置文件路径
        dry_run: 是否为干运行（不实际写入数据库）
    """
    logger.info("=" * 80)
    logger.info("相机配置迁移工具")
    logger.info("=" * 80)
    logger.info(f"YAML文件: {yaml_path}")
    logger.info(f"数据库: {database_url}")
    logger.info(f"模式: {'干运行（预览）' if dry_run else '实际迁移'}")
    logger.info("")

    # 1. 读取YAML配置文件
    if not os.path.exists(yaml_path):
        logger.error(f"YAML文件不存在: {yaml_path}")
        sys.exit(1)

    logger.info("[步骤1/4] 读取YAML配置文件...")
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}
        cameras_yaml = yaml_data.get("cameras", [])
        logger.info(f"✓ 找到 {len(cameras_yaml)} 个相机配置")
    except Exception as e:
        logger.error(f"读取YAML文件失败: {e}")
        sys.exit(1)

    if not cameras_yaml:
        logger.warning("YAML文件中没有相机配置，无需迁移")
        sys.exit(0)

    # 2. 解析并转换为Camera实体
    logger.info("[步骤2/4] 解析相机配置...")
    cameras = []
    for cam_data in cameras_yaml:
        try:
            camera_id = cam_data.get("id")
            if not camera_id:
                logger.warning(f"跳过缺少ID的相机配置: {cam_data.get('name', 'unknown')}")
                continue

            # 转换状态
            status_str = cam_data.get("status", "active")
            if isinstance(status_str, str):
                try:
                    status = CameraStatus(status_str)
                except ValueError:
                    status = (
                        CameraStatus.ACTIVE
                        if cam_data.get("active", True)
                        else CameraStatus.INACTIVE
                    )
            else:
                status = (
                    CameraStatus.ACTIVE
                    if cam_data.get("active", True)
                    else CameraStatus.INACTIVE
                )

            # 转换类型
            camera_type_str = cam_data.get("camera_type", "fixed")
            try:
                camera_type = CameraType(camera_type_str)
            except ValueError:
                camera_type = CameraType.FIXED

            # 转换分辨率
            resolution = None
            if cam_data.get("resolution"):
                if isinstance(cam_data["resolution"], list):
                    resolution = tuple(cam_data["resolution"])
                elif isinstance(cam_data["resolution"], dict):
                    # 处理 {'width': 1920, 'height': 1080} 格式
                    if (
                        "width" in cam_data["resolution"]
                        and "height" in cam_data["resolution"]
                    ):
                        resolution = (
                            cam_data["resolution"]["width"],
                            cam_data["resolution"]["height"],
                        )

            # 构建metadata（包含source等字段）
            metadata = {}
            if "source" in cam_data:
                metadata["source"] = cam_data["source"]
            for key in [
                "regions_file",
                "profile",
                "device",
                "imgsz",
                "auto_tune",
                "auto_start",
                "env",
            ]:
                if key in cam_data:
                    metadata[key] = cam_data[key]

            camera = Camera(
                id=camera_id,
                name=cam_data.get("name", camera_id),
                location=cam_data.get("location", "unknown"),
                status=status,
                camera_type=camera_type,
                resolution=resolution,
                fps=cam_data.get("fps"),
                region_id=cam_data.get("region_id"),
                metadata=metadata,
                created_at=Timestamp.now(),  # 使用当前时间
                updated_at=Timestamp.now(),
            )
            cameras.append(camera)
            logger.info(f"  ✓ 解析相机: {camera_id} ({camera.name})")
        except Exception as e:
            logger.error(f"解析相机配置失败: {e}, data={cam_data}")
            continue

    logger.info(f"✓ 成功解析 {len(cameras)} 个相机")
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

        # 确保cameras表存在
        try:
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
            logger.info("✓ cameras表已确保存在")
        except Exception as e:
            logger.error(f"创建cameras表失败: {e}")
            await conn.close()
            sys.exit(1)

    # 4. 迁移数据
    logger.info("[步骤4/4] 迁移数据到数据库...")
    if dry_run:
        logger.info("  ⚠️  干运行模式，预览迁移操作")
        for camera in cameras:
            logger.info(f"  → 将迁移: {camera.id} ({camera.name})")
        logger.info("")
        logger.info("✓ 预览完成，使用 --no-dry-run 执行实际迁移")
        return

    migrated = 0
    errors = 0

    for camera in cameras:
        try:
            # 检查是否已存在
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM cameras WHERE id = $1)",
                camera.id,
            )

            if exists:
                # 更新现有记录
                resolution_json = (
                    json.dumps(list(camera.resolution)) if camera.resolution else None
                )
                metadata_json = json.dumps(camera.metadata) if camera.metadata else "{}"

                await conn.execute(
                    """
                    UPDATE cameras SET
                        name = $1,
                        location = $2,
                        status = $3,
                        camera_type = $4,
                        resolution = $5,
                        fps = $6,
                        region_id = $7,
                        metadata = $8,
                        updated_at = $9
                    WHERE id = $10
                    """,
                    camera.name,
                    camera.location,
                    camera.status.value,
                    camera.camera_type.value,
                    resolution_json,
                    camera.fps,
                    camera.region_id,
                    metadata_json,
                    camera.updated_at.value,
                    camera.id,
                )
                logger.info(f"  ✓ 更新: {camera.id} ({camera.name})")
                migrated += 1
            else:
                # 插入新记录
                resolution_json = (
                    json.dumps(list(camera.resolution)) if camera.resolution else None
                )
                metadata_json = json.dumps(camera.metadata) if camera.metadata else "{}"

                await conn.execute(
                    """
                    INSERT INTO cameras
                    (id, name, location, status, camera_type, resolution, fps, region_id, metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    camera.id,
                    camera.name,
                    camera.location,
                    camera.status.value,
                    camera.camera_type.value,
                    resolution_json,
                    camera.fps,
                    camera.region_id,
                    metadata_json,
                    camera.created_at.value,
                    camera.updated_at.value,
                )
                logger.info(f"  ✓ 插入: {camera.id} ({camera.name})")
                migrated += 1
        except Exception as e:
            logger.error(f"  ✗ 迁移失败: {camera.id} - {e}")
            errors += 1

    await conn.close()

    # 5. 迁移总结
    logger.info("")
    logger.info("=" * 80)
    logger.info("迁移完成")
    logger.info("=" * 80)
    logger.info(f"总计: {len(cameras)} 个相机")
    logger.info(f"成功: {migrated} 个")
    logger.info(f"失败: {errors} 个")
    logger.info("")
    logger.info("✓ 相机配置已从YAML迁移到数据库")
    logger.info("  现在可以移除CameraService中的YAML写入逻辑")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从YAML迁移相机配置到数据库")
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
    asyncio.run(migrate_cameras(database_url, args.yaml_path, args.dry_run))
