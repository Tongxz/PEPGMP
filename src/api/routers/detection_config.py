"""检测配置管理API"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel, Field

from src.config.unified_params import (
    UnifiedParams,
    save_global_params,
    update_global_param,
)
from src.config.unified_params_loader import load_unified_params_from_db
from src.domain.services.detection_config_service import DetectionConfigService
from src.infrastructure.repositories.postgresql_detection_config_repository import (
    PostgreSQLDetectionConfigRepository,
)
from src.services.database_service import get_db_service

from ..schemas.error_schemas import ErrorCode
from ..utils.error_helpers import raise_http_exception

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/detection-config", tags=["检测配置"])


class HumanDetectionConfig(BaseModel):
    """人体检测配置"""

    confidence_threshold: float = Field(0.5, ge=0.1, le=0.9, description="置信度阈值")
    iou_threshold: float = Field(0.6, ge=0.1, le=1.0, description="IoU阈值")
    min_box_area: int = Field(1500, ge=100, le=10000, description="最小检测框面积")
    min_width: int = Field(50, ge=20, le=200, description="最小宽度")
    min_height: int = Field(80, ge=30, le=300, description="最小高度")
    max_detections: int = Field(15, ge=1, le=50, description="最大检测数量")


class HairnetDetectionConfig(BaseModel):
    """发网检测配置"""

    confidence_threshold: float = Field(0.65, ge=0.1, le=0.9, description="置信度阈值")
    total_score_threshold: float = Field(0.85, ge=0.3, le=1.0, description="总分数阈值")


class BehaviorRecognitionConfig(BaseModel):
    """行为识别配置"""

    confidence_threshold: float = Field(0.65, ge=0.1, le=0.9, description="置信度阈值")
    handwashing_stability_frames: int = Field(3, ge=1, le=10, description="洗手稳定性帧数")
    sanitizing_stability_frames: int = Field(3, ge=1, le=10, description="消毒稳定性帧数")


class DetectionConfigRequest(BaseModel):
    """检测配置请求"""

    human_detection: Optional[HumanDetectionConfig] = None
    hairnet_detection: Optional[HairnetDetectionConfig] = None
    behavior_recognition: Optional[BehaviorRecognitionConfig] = None


class DetectionConfigResponse(BaseModel):
    """检测配置响应"""

    human_detection: HumanDetectionConfig
    hairnet_detection: HairnetDetectionConfig
    behavior_recognition: BehaviorRecognitionConfig
    message: str = "配置获取成功"


async def get_config_service() -> Optional[DetectionConfigService]:
    """获取检测配置服务实例."""
    try:
        db_service = await get_db_service()
        if not db_service.pool:
            logger.warning("数据库连接池未初始化，无法使用数据库配置")
            return None
        config_repository = PostgreSQLDetectionConfigRepository(db_service.pool)
        return DetectionConfigService(config_repository)
    except Exception as e:
        logger.warning(f"创建检测配置服务失败: {e}")
        return None


@router.get("", summary="获取检测配置")
async def get_detection_config(
    camera_id: Optional[str] = Query(None, description="摄像头ID（可选，用于按相机获取配置）"),
) -> DetectionConfigResponse:
    """获取当前检测配置（优先从数据库读取，失败时从YAML读取）"""
    try:
        # 尝试从数据库加载配置
        params: Optional[UnifiedParams] = None
        config_service = await get_config_service()
        if config_service:
            try:
                params = await load_unified_params_from_db(
                    camera_id=camera_id,
                    config_repository=config_service.config_repository,
                )
                logger.debug(f"从数据库加载配置成功: camera_id={camera_id}")
            except Exception as e:
                logger.warning(f"从数据库加载配置失败: {e}，从YAML加载")

        # 如果数据库加载失败，从YAML加载
        if params is None:
            from src.config.unified_params import get_unified_params

            params = get_unified_params()

        return DetectionConfigResponse(
            human_detection=HumanDetectionConfig(
                confidence_threshold=params.human_detection.confidence_threshold,
                iou_threshold=params.human_detection.iou_threshold,
                min_box_area=params.human_detection.min_box_area,
                min_width=params.human_detection.min_width,
                min_height=params.human_detection.min_height,
                max_detections=params.human_detection.max_detections,
            ),
            hairnet_detection=HairnetDetectionConfig(
                confidence_threshold=params.hairnet_detection.confidence_threshold,
                total_score_threshold=params.hairnet_detection.total_score_threshold,
            ),
            behavior_recognition=BehaviorRecognitionConfig(
                confidence_threshold=params.behavior_recognition.confidence_threshold,
                handwashing_stability_frames=params.behavior_recognition.handwashing_stability_frames,
                sanitizing_stability_frames=params.behavior_recognition.sanitizing_stability_frames,
            ),
        )
    except Exception as e:
        logger.error(f"获取检测配置失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="获取检测配置失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.put("", summary="更新检测配置")
async def update_detection_config(  # noqa: C901
    config: DetectionConfigRequest = Body(...),
    camera_id: Optional[str] = Query(None, description="摄像头ID（可选，用于按相机保存配置）"),
    apply_immediately: bool = Query(False, description="是否立即应用（需要重启检测服务）"),
) -> Dict[str, Any]:
    """更新检测配置（同时保存到数据库和YAML）

    注意：配置更新后需要重启检测服务才能生效
    """
    try:
        updated_fields = []

        # 获取配置服务
        config_service = await get_config_service()

        # 更新人体检测配置
        if config.human_detection:
            hd = config.human_detection
            if hd.confidence_threshold is not None:
                if config_service:
                    await config_service.save_config(
                        camera_id,
                        "human_detection",
                        "confidence_threshold",
                        hd.confidence_threshold,
                    )
                update_global_param(
                    "human_detection", "confidence_threshold", hd.confidence_threshold
                )
                updated_fields.append("human_detection.confidence_threshold")
            if hd.iou_threshold is not None:
                if config_service:
                    await config_service.save_config(
                        camera_id, "human_detection", "iou_threshold", hd.iou_threshold
                    )
                update_global_param(
                    "human_detection", "iou_threshold", hd.iou_threshold
                )
                updated_fields.append("human_detection.iou_threshold")
            if hd.min_box_area is not None:
                if config_service:
                    await config_service.save_config(
                        camera_id, "human_detection", "min_box_area", hd.min_box_area
                    )
                update_global_param("human_detection", "min_box_area", hd.min_box_area)
                updated_fields.append("human_detection.min_box_area")
            if hd.min_width is not None:
                if config_service:
                    await config_service.save_config(
                        camera_id, "human_detection", "min_width", hd.min_width
                    )
                update_global_param("human_detection", "min_width", hd.min_width)
                updated_fields.append("human_detection.min_width")
            if hd.min_height is not None:
                if config_service:
                    await config_service.save_config(
                        camera_id, "human_detection", "min_height", hd.min_height
                    )
                update_global_param("human_detection", "min_height", hd.min_height)
                updated_fields.append("human_detection.min_height")
            if hd.max_detections is not None:
                if config_service:
                    await config_service.save_config(
                        camera_id,
                        "human_detection",
                        "max_detections",
                        hd.max_detections,
                    )
                update_global_param(
                    "human_detection", "max_detections", hd.max_detections
                )
                updated_fields.append("human_detection.max_detections")

        # 更新发网检测配置
        if config.hairnet_detection:
            hd = config.hairnet_detection
            if hd.confidence_threshold is not None:
                if config_service:
                    await config_service.save_config(
                        camera_id,
                        "hairnet_detection",
                        "confidence_threshold",
                        hd.confidence_threshold,
                    )
                update_global_param(
                    "hairnet_detection", "confidence_threshold", hd.confidence_threshold
                )
                updated_fields.append("hairnet_detection.confidence_threshold")
            if hd.total_score_threshold is not None:
                if config_service:
                    await config_service.save_config(
                        camera_id,
                        "hairnet_detection",
                        "total_score_threshold",
                        hd.total_score_threshold,
                    )
                update_global_param(
                    "hairnet_detection",
                    "total_score_threshold",
                    hd.total_score_threshold,
                )
                updated_fields.append("hairnet_detection.total_score_threshold")

        # 更新行为识别配置
        if config.behavior_recognition:
            br = config.behavior_recognition
            if br.confidence_threshold is not None:
                if config_service:
                    await config_service.save_config(
                        camera_id,
                        "behavior_recognition",
                        "confidence_threshold",
                        br.confidence_threshold,
                    )
                update_global_param(
                    "behavior_recognition",
                    "confidence_threshold",
                    br.confidence_threshold,
                )
                updated_fields.append("behavior_recognition.confidence_threshold")
            if br.handwashing_stability_frames is not None:
                if config_service:
                    await config_service.save_config(
                        camera_id,
                        "behavior_recognition",
                        "handwashing_stability_frames",
                        br.handwashing_stability_frames,
                    )
                update_global_param(
                    "behavior_recognition",
                    "handwashing_stability_frames",
                    br.handwashing_stability_frames,
                )
                updated_fields.append(
                    "behavior_recognition.handwashing_stability_frames"
                )
            if br.sanitizing_stability_frames is not None:
                if config_service:
                    await config_service.save_config(
                        camera_id,
                        "behavior_recognition",
                        "sanitizing_stability_frames",
                        br.sanitizing_stability_frames,
                    )
                update_global_param(
                    "behavior_recognition",
                    "sanitizing_stability_frames",
                    br.sanitizing_stability_frames,
                )
                updated_fields.append(
                    "behavior_recognition.sanitizing_stability_frames"
                )

        # 保存到YAML文件（作为备份）
        save_global_params()

        # 清除缓存，强制重新加载
        from src.config.unified_params_loader import clear_cache

        clear_cache()

        # 发布配置变更通知到Redis
        try:
            from src.infrastructure.notifications.config_change_notifier import (
                publish_config_change_notification_async,
            )

            # 为每个更新的配置项发布通知
            for field in updated_fields:
                parts = field.split(".")
                if len(parts) >= 2:
                    config_type = parts[0]
                    config_key = parts[1]
                    # 获取配置值（从数据库或请求）
                    config_value = None
                    if config_service:
                        try:
                            config_dict = await config_service.get_config(
                                camera_id, config_type
                            )
                            config_value = config_dict.get(config_key)
                        except Exception as e:
                            logger.warning(f"从数据库获取配置值失败: {e}，从请求中获取")

                    # 如果从数据库获取失败，从请求中获取值
                    if config_value is None:
                        if config_type == "human_detection" and config.human_detection:
                            config_value = getattr(
                                config.human_detection, config_key, None
                            )
                        elif (
                            config_type == "hairnet_detection"
                            and config.hairnet_detection
                        ):
                            config_value = getattr(
                                config.hairnet_detection, config_key, None
                            )
                        elif (
                            config_type == "behavior_recognition"
                            and config.behavior_recognition
                        ):
                            config_value = getattr(
                                config.behavior_recognition, config_key, None
                            )

                    # 发布配置变更通知
                    if config_value is not None:
                        await publish_config_change_notification_async(
                            camera_id=camera_id,
                            config_type=config_type,
                            config_key=config_key,
                            config_value=config_value,
                            change_type="update",
                        )
                    else:
                        logger.warning(
                            f"无法获取配置值: config_type={config_type}, "
                            f"config_key={config_key}，跳过通知发布"
                        )
        except Exception as e:
            logger.warning(f"发布配置变更通知失败: {e}，不影响配置保存")

        logger.info(f"检测配置已更新: {updated_fields}, camera_id={camera_id}")

        return {
            "ok": True,
            "message": "配置已保存",
            "updated_fields": updated_fields,
            "camera_id": camera_id,
            "apply_immediately": apply_immediately,
            "note": "配置已保存到数据库和YAML文件，并已发布变更通知。检测进程将自动重新加载配置。"
            if not apply_immediately
            else "配置已保存，请重启检测服务以应用更改",
        }
    except Exception as e:
        logger.error(f"更新检测配置失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="更新检测配置失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )
