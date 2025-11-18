"""
执行迁移脚本 002: 添加 cameras 表的 status 列
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.database.connection import get_database_pool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def run_migration():
    """执行迁移：添加 cameras 表的缺失列（status 和 region_id）"""
    try:
        # 获取数据库连接池
        pool = await get_database_pool()
        if not pool:
            logger.error("无法获取数据库连接池，请检查 DATABASE_URL 环境变量")
            return False
        
        conn = await pool.acquire()
        try:
            # 需要添加的列
            required_columns = {
                'status': ('VARCHAR(20)', "'inactive'", True),
                'region_id': ('VARCHAR(100)', None, False),
                'metadata': ('JSONB', "'{}'::jsonb", True),
            }
            
            added_count = 0
            for column_name, (column_type, default_value, update_existing) in required_columns.items():
                # 检查列是否存在
                column_exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_schema = 'public'
                        AND table_name = 'cameras'
                        AND column_name = $1
                    )
                    """,
                    column_name
                )
                
                if column_exists:
                    logger.info(f"{column_name} 列已存在，跳过")
                    continue
                
                logger.info(f"开始添加 {column_name} 列到 cameras 表...")
                
                try:
                    # 添加列
                    if default_value:
                        await conn.execute(
                            f"""
                            ALTER TABLE cameras
                            ADD COLUMN {column_name} {column_type} DEFAULT {default_value}
                            """
                        )
                    else:
                        await conn.execute(
                            f"""
                            ALTER TABLE cameras
                            ADD COLUMN {column_name} {column_type}
                            """
                        )
                    
                    # 如果列有默认值且需要更新现有记录
                    if default_value and update_existing:
                        result = await conn.execute(
                            f"""
                            UPDATE cameras
                            SET {column_name} = {default_value}
                            WHERE {column_name} IS NULL
                            """
                        )
                        logger.info(f"已添加 {column_name} 列，并更新了现有记录")
                    else:
                        logger.info(f"已添加 {column_name} 列")
                    
                    added_count += 1
                except Exception as col_error:
                    if 'already exists' in str(col_error).lower():
                        logger.debug(f"{column_name} 列已存在（并发情况），跳过")
                    else:
                        logger.error(f"添加 {column_name} 列失败: {col_error}")
                        raise
            
            if added_count > 0:
                logger.info(f"✅ 迁移成功！已添加 {added_count} 个列")
            else:
                logger.info("✅ 所有必需的列都已存在，无需迁移")
            
            return True
            
        finally:
            await pool.release(conn)
            
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("执行数据库迁移: 添加 cameras 表的 status 列")
    logger.info("=" * 60)
    
    success = asyncio.run(run_migration())
    
    if success:
        logger.info("=" * 60)
        logger.info("✅ 迁移完成")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("❌ 迁移失败")
        logger.error("=" * 60)
        sys.exit(1)

