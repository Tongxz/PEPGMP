"""数据导出API路由模块.

提供检测记录、统计数据、违规记录的CSV/Excel导出功能.
所有接口统一使用领域服务，符合DDD架构要求.
"""

import csv
import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..schemas.error_schemas import ErrorCode
from ..utils.error_helpers import raise_http_exception

router = APIRouter(prefix="/api/v1/export", tags=["Export"])
logger = logging.getLogger(__name__)

# 领域服务依赖
try:
    from src.services.detection_service_domain import get_detection_service_domain
except ImportError:
    get_detection_service_domain = None


def _ensure_domain_service():
    """确保领域服务可用，如果不可用则抛出HTTP异常."""
    if get_detection_service_domain is None:
        raise raise_http_exception(
            status_code=503,
            message="检测领域服务不可用，请联系系统管理员",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )
    service = get_detection_service_domain()
    if service is None:
        raise raise_http_exception(
            status_code=503,
            message="检测领域服务未初始化，请联系系统管理员",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )
    return service


def _generate_csv(data: List[Dict[str, Any]], headers: List[str]) -> io.StringIO:
    """生成CSV格式的数据流.

    Args:
        data: 数据列表
        headers: CSV表头列表

    Returns:
        CSV字符串流
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()

    for row in data:
        # 处理嵌套字典和列表
        processed_row = {}
        for key in headers:
            value = row.get(key)
            if isinstance(value, dict):
                processed_row[key] = str(value)
            elif isinstance(value, list):
                processed_row[key] = str(value)
            elif isinstance(value, datetime):
                processed_row[key] = value.isoformat()
            else:
                processed_row[key] = value
        writer.writerow(processed_row)

    output.seek(0)
    return output


def _process_row_for_csv(row: Dict[str, Any], headers: List[str]) -> Dict[str, Any]:
    """处理单行数据，转换为CSV格式.

    Args:
        row: 原始数据行
        headers: CSV表头列表

    Returns:
        处理后的数据行
    """
    processed_row = {}
    for key in headers:
        value = row.get(key)
        if isinstance(value, dict):
            processed_row[key] = str(value)
        elif isinstance(value, list):
            processed_row[key] = str(value)
        elif isinstance(value, datetime):
            processed_row[key] = value.isoformat()
        elif value is None:
            processed_row[key] = ""
        else:
            processed_row[key] = value
    return processed_row


async def _generate_csv_stream(
    headers: List[str], data_generator, batch_size: int = 1000
) -> bytes:
    """流式生成CSV数据.

    Args:
        headers: CSV表头列表
        data_generator: 数据生成器（异步生成器）
        batch_size: 每批处理的数据量

    Returns:
        CSV字节数据
    """
    output = io.BytesIO()
    # 写入BOM（UTF-8-BOM），支持Excel中文
    output.write("\ufeff".encode("utf-8"))

    # 创建CSV writer
    writer = csv.DictWriter(
        io.TextIOWrapper(output, encoding="utf-8"),
        fieldnames=headers,
        extrasaction="ignore",
    )
    writer.writeheader()

    # 流式处理数据
    batch = []
    async for row in data_generator:
        batch.append(_process_row_for_csv(row, headers))
        if len(batch) >= batch_size:
            for processed_row in batch:
                writer.writerow(processed_row)
            batch = []
            # 刷新输出缓冲区
            output.flush()

    # 处理剩余数据
    if batch:
        for processed_row in batch:
            writer.writerow(processed_row)

    output.seek(0)
    return output.getvalue()


@router.get("/detection-records", summary="导出检测记录")
async def export_detection_records(  # noqa: C901
    camera_id: Optional[str] = Query(None, description="摄像头ID，不提供则导出所有"),
    start_time: Optional[str] = Query(None, description="开始时间（ISO格式）"),
    end_time: Optional[str] = Query(None, description="结束时间（ISO格式）"),
    format: str = Query("csv", description="导出格式: csv, excel"),
    limit: int = Query(5000, ge=1, le=50000, description="导出记录数量限制（默认5000，避免超时）"),
) -> StreamingResponse:
    """导出检测记录为CSV或Excel格式.

    Args:
        camera_id: 摄像头ID过滤
        start_time: 开始时间（ISO格式字符串）
        end_time: 结束时间（ISO格式字符串）
        format: 导出格式（csv或excel）
        limit: 导出记录数量限制

    Returns:
        CSV或Excel文件流

    Raises:
        HTTPException: 如果领域服务不可用或导出失败
    """
    try:
        domain_service = _ensure_domain_service()

        # 解析时间参数
        start_datetime = None
        end_datetime = None
        if start_time:
            try:
                start_datetime = datetime.fromisoformat(
                    start_time.replace("Z", "+00:00")
                )
            except ValueError:
                raise raise_http_exception(
                    status_code=400,
                    message="开始时间格式错误，请使用ISO格式",
                    error_code=ErrorCode.VALIDATION_ERROR,
                )
        if end_time:
            try:
                end_datetime = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except ValueError:
                raise raise_http_exception(
                    status_code=400,
                    message="结束时间格式错误，请使用ISO格式",
                    error_code=ErrorCode.VALIDATION_ERROR,
                )

        # 检查camera_id
        if not camera_id or camera_id == "all":
            raise raise_http_exception(
                status_code=400,
                message="导出检测记录需要指定camera_id，暂不支持导出所有摄像头的数据",
                error_code=ErrorCode.VALIDATION_ERROR,
            )

        # 定义CSV表头
        headers = [
            "id",
            "camera_id",
            "timestamp",
            "frame_number",
            "frame_id",
            "person_count",
            "hairnet_violations",
            "handwash_events",
            "sanitize_events",
            "processing_time",
            "fps",
        ]

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"detection_records_{timestamp}.csv"
        if camera_id and camera_id != "all":
            filename = f"detection_records_{camera_id}_{timestamp}.csv"

        # 先快速检查是否有数据（只查询1条记录）
        quick_check = await domain_service.get_detection_records_by_camera(
            camera_id=camera_id,
            limit=1,
            offset=0,
            start_time=start_datetime,
            end_time=end_datetime,
        )

        if not quick_check.get("records"):
            raise raise_http_exception(
                status_code=404,
                message="没有找到符合条件的检测记录",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        # 使用流式生成器，边查询边生成CSV
        async def generate_csv_chunks():
            """流式生成CSV数据块."""
            # 写入BOM（UTF-8-BOM），支持Excel中文
            yield "\ufeff".encode("utf-8")

            # 创建CSV writer的缓冲区
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()

            # 发送表头
            header_line = buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)
            yield header_line.encode("utf-8")

            # 分批获取数据并生成CSV
            offset = 0
            batch_size = 500  # 减小批次大小，更快响应
            total_count = 0

            while total_count < limit:
                batch_limit = min(batch_size, limit - total_count)

                try:
                    result = await domain_service.get_detection_records_by_camera(
                        camera_id=camera_id,
                        limit=batch_limit,
                        offset=offset,
                        start_time=start_datetime,
                        end_time=end_datetime,
                    )

                    records = result.get("records", [])
                    if not records:
                        break

                    # 处理当前批次的数据
                    for record in records:
                        processed_row = _process_row_for_csv(record, headers)
                        writer.writerow(processed_row)

                    # 每批次发送一次数据
                    batch_data = buffer.getvalue()
                    if batch_data:
                        yield batch_data.encode("utf-8")
                        buffer.seek(0)
                        buffer.truncate(0)

                    total_count += len(records)
                    offset += len(records)

                    # 如果返回的记录数小于批次大小，说明已经到末尾
                    if len(records) < batch_limit:
                        break

                except Exception as e:
                    logger.error(f"导出过程中出错: {e}", exc_info=True)
                    break

            # 发送剩余数据
            remaining = buffer.getvalue()
            if remaining:
                yield remaining.encode("utf-8")

            logger.info(f"导出完成: 共 {total_count} 条记录")

        return StreamingResponse(
            generate_csv_chunks(),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出检测记录失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="导出检测记录失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.get("/violations", summary="导出违规记录")
async def export_violations(
    camera_id: Optional[str] = Query(None, description="摄像头ID，不提供则导出所有"),
    status: Optional[str] = Query(None, description="违规状态过滤"),
    violation_type: Optional[str] = Query(None, description="违规类型过滤"),
    format: str = Query("csv", description="导出格式: csv, excel"),
    limit: int = Query(5000, ge=1, le=50000, description="导出记录数量限制（默认5000，避免超时）"),
) -> StreamingResponse:
    """导出违规记录为CSV或Excel格式.

    Args:
        camera_id: 摄像头ID过滤
        status: 违规状态过滤
        violation_type: 违规类型过滤
        format: 导出格式（csv或excel）
        limit: 导出记录数量限制

    Returns:
        CSV或Excel文件流

    Raises:
        HTTPException: 如果领域服务不可用或导出失败
    """
    try:
        domain_service = _ensure_domain_service()

        # 定义CSV表头
        headers = [
            "id",
            "detection_id",
            "camera_id",
            "timestamp",
            "violation_type",
            "track_id",
            "confidence",
            "status",
            "notes",
            "handled_by",
            "handled_at",
        ]

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"violations_{timestamp}.csv"
        if camera_id and camera_id != "all":
            filename = f"violations_{camera_id}_{timestamp}.csv"

        # 先快速检查是否有数据
        quick_check = await domain_service.get_violation_details(
            camera_id=camera_id if camera_id != "all" else None,
            status=status,
            violation_type=violation_type,
            limit=1,
            offset=0,
        )

        if not quick_check.get("violations"):
            raise raise_http_exception(
                status_code=404,
                message="没有找到符合条件的违规记录",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        # 使用流式生成器
        async def generate_csv_chunks():
            """流式生成CSV数据块."""
            # 写入BOM（UTF-8-BOM），支持Excel中文
            yield "\ufeff".encode("utf-8")

            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()

            # 发送表头
            header_line = buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)
            yield header_line.encode("utf-8")

            # 分批获取数据并生成CSV
            offset = 0
            batch_size = 500
            total_count = 0

            while total_count < limit:
                batch_limit = min(batch_size, limit - total_count)

                try:
                    result = await domain_service.get_violation_details(
                        camera_id=camera_id if camera_id != "all" else None,
                        status=status,
                        violation_type=violation_type,
                        limit=batch_limit,
                        offset=offset,
                    )

                    violations = result.get("violations", [])
                    if not violations:
                        break

                    # 处理当前批次的数据
                    for violation in violations:
                        processed_row = _process_row_for_csv(violation, headers)
                        writer.writerow(processed_row)

                    # 每批次发送一次数据
                    batch_data = buffer.getvalue()
                    if batch_data:
                        yield batch_data.encode("utf-8")
                        buffer.seek(0)
                        buffer.truncate(0)

                    total_count += len(violations)
                    offset += len(violations)

                    if len(violations) < batch_limit:
                        break

                except Exception as e:
                    logger.error(f"导出过程中出错: {e}", exc_info=True)
                    break

            # 发送剩余数据
            remaining = buffer.getvalue()
            if remaining:
                yield remaining.encode("utf-8")

            logger.info(f"导出完成: 共 {total_count} 条违规记录")

        return StreamingResponse(
            generate_csv_chunks(),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出违规记录失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="导出违规记录失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )


@router.get("/statistics", summary="导出统计数据")
async def export_statistics(
    camera_id: Optional[str] = Query(None, description="摄像头ID，不提供则导出所有"),
    start_time: Optional[str] = Query(None, description="开始时间（ISO格式）"),
    end_time: Optional[str] = Query(None, description="结束时间（ISO格式）"),
    format: str = Query("csv", description="导出格式: csv, excel"),
    days: int = Query(7, ge=1, le=90, description="统计天数（如果未提供时间范围）"),
) -> StreamingResponse:
    """导出统计数据为CSV或Excel格式.

    Args:
        camera_id: 摄像头ID过滤
        start_time: 开始时间（ISO格式字符串）
        end_time: 结束时间（ISO格式字符串）
        format: 导出格式（csv或excel）
        days: 统计天数（如果未提供时间范围）

    Returns:
        CSV或Excel文件流

    Raises:
        HTTPException: 如果领域服务不可用或导出失败
    """
    try:
        domain_service = _ensure_domain_service()

        # 解析时间参数
        from datetime import timedelta

        start_datetime = None
        end_datetime = None

        if start_time:
            try:
                start_datetime = datetime.fromisoformat(
                    start_time.replace("Z", "+00:00")
                )
            except ValueError:
                raise raise_http_exception(
                    status_code=400,
                    message="开始时间格式错误，请使用ISO格式",
                    error_code=ErrorCode.VALIDATION_ERROR,
                )

        if end_time:
            try:
                end_datetime = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except ValueError:
                raise raise_http_exception(
                    status_code=400,
                    message="结束时间格式错误，请使用ISO格式",
                    error_code=ErrorCode.VALIDATION_ERROR,
                )

        # 如果没有提供时间范围，使用默认天数
        if not start_datetime or not end_datetime:
            end_datetime = datetime.utcnow()
            start_datetime = end_datetime - timedelta(days=days)

        # 计算天数（如果提供了时间范围）
        if start_datetime and end_datetime:
            days = (end_datetime - start_datetime).days + 1
        else:
            days = days

        # 获取每日统计数据
        # 注意：get_daily_statistics只接受days和camera_id参数，不支持start_time和end_time
        daily_stats = await domain_service.get_daily_statistics(
            days=days,
            camera_id=camera_id if camera_id and camera_id != "all" else None,
        )

        if not daily_stats:
            raise raise_http_exception(
                status_code=404,
                message="没有找到符合条件的统计数据",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        # 定义CSV表头
        headers = [
            "date",
            "camera_id",
            "total_records",
            "total_persons",
            "total_violations",
            "compliance_rate",
            "avg_confidence",
        ]

        # 转换为列表格式（统计数据通常不大，可以直接生成）
        stats_list = []
        for stat in daily_stats:
            stats_list.append(
                {
                    "date": stat.get("date"),
                    "camera_id": stat.get("camera_id", "all"),
                    "total_records": stat.get("total_records", 0),
                    "total_persons": stat.get("total_persons", 0),
                    "total_violations": stat.get("total_violations", 0),
                    "compliance_rate": stat.get("compliance_rate", 0.0),
                    "avg_confidence": stat.get("avg_confidence", 0.0),
                }
            )

        if not stats_list:
            raise raise_http_exception(
                status_code=404,
                message="没有找到符合条件的统计数据",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
            )

        # 生成CSV（统计数据量小，可以直接生成）
        csv_stream = _generate_csv(stats_list, headers)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"statistics_{timestamp}.csv"
        if camera_id and camera_id != "all":
            filename = f"statistics_{camera_id}_{timestamp}.csv"

        return StreamingResponse(
            iter([csv_stream.getvalue().encode("utf-8-sig")]),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出统计数据失败: {e}", exc_info=True)
        raise raise_http_exception(
            status_code=500,
            message="导出统计数据失败",
            error_code=ErrorCode.DATABASE_ERROR,
            details=str(e),
        )
