"""PostgreSQL检测参数配置仓储实现."""

import json
import logging
from typing import Any, Dict, List, Optional

from asyncpg import Pool

from src.domain.repositories.detection_config_repository import (
    IDetectionConfigRepository,
)
from src.interfaces.repositories.detection_repository_interface import RepositoryError

logger = logging.getLogger(__name__)


class PostgreSQLDetectionConfigRepository(IDetectionConfigRepository):
    """PostgreSQL检测参数配置仓储实现."""

    def __init__(self, pool: Pool):
        """初始化PostgreSQL检测参数配置仓储.

        Args:
            pool: PostgreSQL连接池
        """
        self.pool = pool

    async def _get_connection(self):
        """获取数据库连接."""
        return await self.pool.acquire()

    async def _ensure_table_exists(self):
        """确保detection_configs表存在."""
        try:
            conn = await self._get_connection()
            try:
                # 检查表是否存在
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
                    logger.warning("detection_configs表不存在，创建表...")
                    # 读取SQL文件
                    from pathlib import Path

                    project_root = Path(__file__).parent.parent.parent.parent
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
                        logger.info("detection_configs表已创建")
                    else:
                        logger.error(f"SQL文件不存在: {sql_file}")
                        raise RepositoryError(f"SQL文件不存在: {sql_file}")

                logger.debug("detection_configs表已确保存在")
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"确保detection_configs表存在失败: {e}")
            raise RepositoryError(f"确保detection_configs表存在失败: {e}")

    async def save(
        self,
        camera_id: Optional[str],
        config_type: str,
        config_key: str,
        config_value: Any,
        description: Optional[str] = None,
    ) -> int:
        """保存检测参数配置."""
        await self._ensure_table_exists()

        try:
            conn = await self._get_connection()
            try:
                # 检查配置项是否已存在
                existing = await conn.fetchrow(
                    """
                    SELECT id FROM detection_configs
                    WHERE (camera_id = $1 OR (camera_id IS NULL AND $1 IS NULL))
                    AND config_type = $2
                    AND config_key = $3
                    """,
                    camera_id,
                    config_type,
                    config_key,
                )

                # 将config_value转换为JSONB
                if isinstance(config_value, (dict, list)):
                    config_value_jsonb = json.dumps(config_value)
                else:
                    config_value_jsonb = json.dumps(config_value)

                if existing:
                    # 更新现有配置项
                    await conn.execute(
                        """
                        UPDATE detection_configs
                        SET config_value = $1::jsonb,
                            description = $2,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = $3
                        """,
                        config_value_jsonb,
                        description,
                        existing["id"],
                    )
                    logger.debug(
                        f"更新配置: camera_id={camera_id}, config_type={config_type}, "
                        f"config_key={config_key}, config_value={config_value}"
                    )
                    return existing["id"]
                else:
                    # 插入新配置项
                    result = await conn.fetchrow(
                        """
                        INSERT INTO detection_configs (camera_id, config_type, config_key, config_value, description)
                        VALUES ($1, $2, $3, $4::jsonb, $5)
                        RETURNING id
                        """,
                        camera_id,
                        config_type,
                        config_key,
                        config_value_jsonb,
                        description,
                    )
                    logger.debug(
                        f"插入配置: camera_id={camera_id}, config_type={config_type}, "
                        f"config_key={config_key}, config_value={config_value}"
                    )
                    return result["id"]
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise RepositoryError(f"保存配置失败: {e}")

    async def find_by_camera_and_type(
        self, camera_id: Optional[str], config_type: str
    ) -> Dict[str, Any]:
        """根据摄像头ID和配置类型查找配置."""
        await self._ensure_table_exists()

        try:
            conn = await self._get_connection()
            try:
                config_dict = {}

                # 先获取全局配置（camera_id IS NULL）
                global_rows = await conn.fetch(
                    """
                    SELECT config_key, config_value
                    FROM detection_configs
                    WHERE config_type = $1
                    AND camera_id IS NULL
                    """,
                    config_type,
                )
                for row in global_rows:
                    config_key = row["config_key"]
                    config_value = row["config_value"]
                    # 如果config_value是字符串，尝试解析为JSON
                    if isinstance(config_value, str):
                        try:
                            config_value = json.loads(config_value)
                        except json.JSONDecodeError:
                            pass
                    config_dict[config_key] = config_value

                # 如果有camera_id，获取相机特定配置并覆盖全局配置
                if camera_id is not None:
                    camera_rows = await conn.fetch(
                        """
                        SELECT config_key, config_value
                        FROM detection_configs
                        WHERE config_type = $1
                        AND camera_id = $2
                        """,
                        config_type,
                        camera_id,
                    )
                    for row in camera_rows:
                        config_key = row["config_key"]
                        config_value = row["config_value"]
                        # 如果config_value是字符串，尝试解析为JSON
                        if isinstance(config_value, str):
                            try:
                                config_value = json.loads(config_value)
                            except json.JSONDecodeError:
                                pass
                        # 相机特定配置覆盖全局配置
                        config_dict[config_key] = config_value

                logger.debug(
                    f"查找配置: camera_id={camera_id}, config_type={config_type}, "
                    f"找到 {len(config_dict)} 个配置项"
                )
                return config_dict
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"查找配置失败: {e}")
            raise RepositoryError(f"查找配置失败: {e}")

    async def find_all_by_type(self, config_type: str) -> List[Dict[str, Any]]:
        """查找指定类型的所有配置（包括全局和按相机的）."""
        await self._ensure_table_exists()

        try:
            conn = await self._get_connection()
            try:
                rows = await conn.fetch(
                    """
                    SELECT camera_id, config_key, config_value, description
                    FROM detection_configs
                    WHERE config_type = $1
                    ORDER BY camera_id NULLS LAST
                    """,
                    config_type,
                )

                config_list = []
                for row in rows:
                    config_value = row["config_value"]
                    # 如果config_value是字符串，尝试解析为JSON
                    if isinstance(config_value, str):
                        try:
                            config_value = json.loads(config_value)
                        except json.JSONDecodeError:
                            pass

                    config_list.append(
                        {
                            "camera_id": row["camera_id"],
                            "config_key": row["config_key"],
                            "config_value": config_value,
                            "description": row["description"],
                        }
                    )

                logger.debug(
                    f"查找所有配置: config_type={config_type}, 找到 {len(config_list)} 个配置项"
                )
                return config_list
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"查找所有配置失败: {e}")
            raise RepositoryError(f"查找所有配置失败: {e}")

    async def find_all(self) -> Dict[str, Dict[str, Any]]:
        """查找所有配置."""
        await self._ensure_table_exists()

        try:
            conn = await self._get_connection()
            try:
                rows = await conn.fetch(
                    """
                    SELECT camera_id, config_type, config_key, config_value
                    FROM detection_configs
                    ORDER BY config_type, camera_id NULLS LAST
                    """
                )

                # 构建配置字典，按config_type分组
                config_dict = {}
                for row in rows:
                    config_type = row["config_type"]
                    camera_id = row["camera_id"]

                    if config_type not in config_dict:
                        config_dict[config_type] = {}

                    # 构建键（全局配置使用config_key，按相机的配置使用camera_id:config_key）
                    if camera_id is None:
                        key = row["config_key"]
                    else:
                        key = f"{camera_id}:{row['config_key']}"

                    config_value = row["config_value"]
                    # 如果config_value是字符串，尝试解析为JSON
                    if isinstance(config_value, str):
                        try:
                            config_value = json.loads(config_value)
                        except json.JSONDecodeError:
                            pass

                    config_dict[config_type][key] = {
                        "camera_id": camera_id,
                        "config_key": row["config_key"],
                        "config_value": config_value,
                    }

                logger.debug(f"查找所有配置: 找到 {len(config_dict)} 个配置类型")
                return config_dict
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"查找所有配置失败: {e}")
            raise RepositoryError(f"查找所有配置失败: {e}")

    async def delete(
        self, camera_id: Optional[str], config_type: str, config_key: str
    ) -> bool:
        """删除配置项."""
        await self._ensure_table_exists()

        try:
            conn = await self._get_connection()
            try:
                result = await conn.execute(
                    """
                    DELETE FROM detection_configs
                    WHERE (camera_id = $1 OR (camera_id IS NULL AND $1 IS NULL))
                    AND config_type = $2
                    AND config_key = $3
                    """,
                    camera_id,
                    config_type,
                    config_key,
                )
                deleted = result == "DELETE 1"
                logger.debug(
                    f"删除配置: camera_id={camera_id}, config_type={config_type}, "
                    f"config_key={config_key}, 成功={deleted}"
                )
                return deleted
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"删除配置失败: {e}")
            raise RepositoryError(f"删除配置失败: {e}")

    async def exists(
        self, camera_id: Optional[str], config_type: str, config_key: str
    ) -> bool:
        """检查配置项是否存在."""
        await self._ensure_table_exists()

        try:
            conn = await self._get_connection()
            try:
                result = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM detection_configs
                        WHERE (camera_id = $1 OR (camera_id IS NULL AND $1 IS NULL))
                        AND config_type = $2
                        AND config_key = $3
                    )
                    """,
                    camera_id,
                    config_type,
                    config_key,
                )
                return bool(result)
            finally:
                await self.pool.release(conn)
        except Exception as e:
            logger.error(f"检查配置项是否存在失败: {e}")
            raise RepositoryError(f"检查配置项是否存在失败: {e}")
