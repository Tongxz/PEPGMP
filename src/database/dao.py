"""
数据访问层 (DAO)
提供数据集、部署、工作流等实体的CRUD操作
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Dataset,
    Deployment,
    ModelRegistry,
    Workflow,
    WorkflowRun,
)

logger = logging.getLogger(__name__)


class DatasetDAO:
    """数据集数据访问对象"""

    @staticmethod
    async def create(session: AsyncSession, dataset_data: Dict[str, Any]) -> Dataset:
        """创建数据集"""
        # 处理时区问题：如果传入的datetime是带时区的，转换为不带时区的（naive）
        # 因为数据库字段是 TIMESTAMP WITHOUT TIME ZONE
        processed_data = dataset_data.copy()

        # 处理 created_at
        if "created_at" in processed_data:
            created_at = processed_data["created_at"]
            if isinstance(created_at, datetime) and created_at.tzinfo is not None:
                # 转换为UTC时间，然后移除时区信息
                processed_data["created_at"] = created_at.astimezone(
                    timezone.utc
                ).replace(tzinfo=None)

        # 处理 updated_at
        if "updated_at" in processed_data:
            updated_at = processed_data["updated_at"]
            if isinstance(updated_at, datetime) and updated_at.tzinfo is not None:
                # 转换为UTC时间，然后移除时区信息
                processed_data["updated_at"] = updated_at.astimezone(
                    timezone.utc
                ).replace(tzinfo=None)

        dataset = Dataset(**processed_data)
        session.add(dataset)
        await session.commit()
        await session.refresh(dataset)
        logger.info(f"创建数据集: {dataset.id}")
        return dataset

    @staticmethod
    async def get_by_id(session: AsyncSession, dataset_id: str) -> Optional[Dataset]:
        """根据ID获取数据集"""
        result = await session.execute(select(Dataset).where(Dataset.id == dataset_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(
        session: AsyncSession,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dataset]:
        """获取所有数据集"""
        query = select(Dataset)

        if status:
            query = query.where(Dataset.status == status)

        query = query.offset(offset).limit(limit).order_by(Dataset.created_at.desc())

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update(
        session: AsyncSession, dataset_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dataset]:
        """更新数据集"""
        update_data["updated_at"] = datetime.utcnow()

        result = await session.execute(
            update(Dataset)
            .where(Dataset.id == dataset_id)
            .values(**update_data)
            .returning(Dataset)
        )

        dataset = result.scalar_one_or_none()
        if dataset:
            await session.commit()
            logger.info(f"更新数据集: {dataset_id}")

        return dataset

    @staticmethod
    async def delete(session: AsyncSession, dataset_id: str) -> bool:
        """删除数据集"""
        result = await session.execute(delete(Dataset).where(Dataset.id == dataset_id))
        await session.commit()

        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"删除数据集: {dataset_id}")

        return deleted

    @staticmethod
    async def count(session: AsyncSession, status: Optional[str] = None) -> int:
        """统计数据集数量"""
        query = select(func.count(Dataset.id))

        if status:
            query = query.where(Dataset.status == status)

        result = await session.execute(query)
        return result.scalar() or 0


class DeploymentDAO:
    """部署数据访问对象"""

    @staticmethod
    async def create(
        session: AsyncSession, deployment_data: Dict[str, Any]
    ) -> Deployment:
        """创建部署"""
        deployment = Deployment(**deployment_data)
        session.add(deployment)
        await session.commit()
        await session.refresh(deployment)
        logger.info(f"创建部署: {deployment.id}")
        return deployment

    @staticmethod
    async def get_by_id(
        session: AsyncSession, deployment_id: str
    ) -> Optional[Deployment]:
        """根据ID获取部署"""
        result = await session.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(session: AsyncSession) -> List[Deployment]:
        """获取所有部署"""
        result = await session.execute(
            select(Deployment).order_by(Deployment.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def update(
        session: AsyncSession, deployment_id: str, update_data: Dict[str, Any]
    ) -> Optional[Deployment]:
        """更新部署"""
        update_data["updated_at"] = datetime.utcnow()

        result = await session.execute(
            update(Deployment)
            .where(Deployment.id == deployment_id)
            .values(**update_data)
            .returning(Deployment)
        )

        deployment = result.scalar_one_or_none()
        if deployment:
            await session.commit()
            logger.info(f"更新部署: {deployment_id}")

        return deployment

    @staticmethod
    async def delete(session: AsyncSession, deployment_id: str) -> bool:
        """删除部署"""
        result = await session.execute(
            delete(Deployment).where(Deployment.id == deployment_id)
        )
        await session.commit()

        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"删除部署: {deployment_id}")

        return deleted

    @staticmethod
    async def update_metrics(
        session: AsyncSession, deployment_id: str, metrics: Dict[str, Any]
    ) -> Optional[Deployment]:
        """更新部署指标"""
        result = await session.execute(
            update(Deployment)
            .where(Deployment.id == deployment_id)
            .values(**metrics, updated_at=datetime.utcnow())
            .returning(Deployment)
        )

        deployment = result.scalar_one_or_none()
        if deployment:
            await session.commit()

        return deployment


class WorkflowDAO:
    """工作流数据访问对象"""

    @staticmethod
    async def create(session: AsyncSession, workflow_data: Dict[str, Any]) -> Workflow:
        """创建工作流"""
        workflow = Workflow(**workflow_data)
        session.add(workflow)
        await session.commit()
        await session.refresh(workflow)
        logger.info(f"创建工作流: {workflow.id}")
        return workflow

    @staticmethod
    async def get_by_id(session: AsyncSession, workflow_id: str) -> Optional[Workflow]:
        """根据ID获取工作流"""
        result = await session.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(session: AsyncSession) -> List[Workflow]:
        """获取所有工作流"""
        result = await session.execute(
            select(Workflow).order_by(Workflow.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def update(
        session: AsyncSession, workflow_id: str, update_data: Dict[str, Any]
    ) -> Optional[Workflow]:
        """更新工作流"""
        # 过滤掉非数据库字段（虚拟字段和只读字段）
        # recent_runs 是 to_dict() 返回的虚拟字段，不是数据库列
        # id, created_at 是只读字段，不应该被更新
        excluded_fields = {"id", "created_at", "recent_runs"}
        filtered_data = {
            k: v for k, v in update_data.items() if k not in excluded_fields
        }
        
        filtered_data["updated_at"] = datetime.utcnow()

        result = await session.execute(
            update(Workflow)
            .where(Workflow.id == workflow_id)
            .values(**filtered_data)
            .returning(Workflow)
        )

        workflow = result.scalar_one_or_none()
        if workflow:
            await session.commit()
            logger.info(f"更新工作流: {workflow_id}")

        return workflow

    @staticmethod
    async def delete(session: AsyncSession, workflow_id: str) -> bool:
        """删除工作流"""
        # 先删除相关的运行记录
        await session.execute(
            delete(WorkflowRun).where(WorkflowRun.workflow_id == workflow_id)
        )

        # 再删除工作流
        result = await session.execute(
            delete(Workflow).where(Workflow.id == workflow_id)
        )
        await session.commit()

        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"删除工作流: {workflow_id}")

        return deleted

    @staticmethod
    async def get_with_recent_runs(
        session: AsyncSession, workflow_id: str, limit: int = 5
    ) -> Optional[Workflow]:
        """获取工作流及其最近运行记录"""
        # 获取工作流
        workflow_result = await session.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        workflow = workflow_result.scalar_one_or_none()

        if workflow:
            # 获取最近运行记录
            runs_result = await session.execute(
                select(WorkflowRun)
                .where(WorkflowRun.workflow_id == workflow_id)
                .order_by(WorkflowRun.started_at.desc())
                .limit(limit)
            )
            recent_runs = runs_result.scalars().all()

            # 将运行记录添加到工作流对象
            workflow_dict = workflow.to_dict()
            workflow_dict["recent_runs"] = [run.to_dict() for run in recent_runs]

            return workflow_dict

        return None


class WorkflowRunDAO:
    """工作流运行记录数据访问对象"""

    @staticmethod
    async def create(session: AsyncSession, run_data: Dict[str, Any]) -> WorkflowRun:
        """创建运行记录"""
        # 处理时区问题：如果传入的datetime是带时区的，转换为不带时区的（naive）
        # 因为数据库字段是 TIMESTAMP WITHOUT TIME ZONE
        processed_data = run_data.copy()
        
        # 处理 started_at
        if "started_at" in processed_data:
            started_at = processed_data["started_at"]
            if isinstance(started_at, datetime) and started_at.tzinfo is not None:
                # 转换为UTC时间，然后移除时区信息
                processed_data["started_at"] = started_at.astimezone(
                    timezone.utc
                ).replace(tzinfo=None)
        
        # 处理 ended_at
        if "ended_at" in processed_data:
            ended_at = processed_data["ended_at"]
            if isinstance(ended_at, datetime) and ended_at.tzinfo is not None:
                # 转换为UTC时间，然后移除时区信息
                processed_data["ended_at"] = ended_at.astimezone(
                    timezone.utc
                ).replace(tzinfo=None)
        
        # 处理 created_at（如果传入）
        if "created_at" in processed_data:
            created_at = processed_data["created_at"]
            if isinstance(created_at, datetime) and created_at.tzinfo is not None:
                # 转换为UTC时间，然后移除时区信息
                processed_data["created_at"] = created_at.astimezone(
                    timezone.utc
                ).replace(tzinfo=None)
        
        run = WorkflowRun(**processed_data)
        session.add(run)
        await session.commit()
        await session.refresh(run)
        logger.info(f"创建工作流运行记录: {run.id}")
        return run

    @staticmethod
    async def get_by_id(session: AsyncSession, run_id: str) -> Optional[WorkflowRun]:
        """根据ID获取运行记录"""
        result = await session.execute(
            select(WorkflowRun).where(WorkflowRun.id == run_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_workflow_id(
        session: AsyncSession, workflow_id: str, limit: int = 10
    ) -> List[WorkflowRun]:
        """根据工作流ID获取运行记录"""
        result = await session.execute(
            select(WorkflowRun)
            .where(WorkflowRun.workflow_id == workflow_id)
            .order_by(WorkflowRun.started_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def update(
        session: AsyncSession, run_id: str, update_data: Dict[str, Any]
    ) -> Optional[WorkflowRun]:
        """更新运行记录"""
        result = await session.execute(
            update(WorkflowRun)
            .where(WorkflowRun.id == run_id)
            .values(**update_data)
            .returning(WorkflowRun)
        )

        run = result.scalar_one_or_none()
        if run:
            await session.commit()
            logger.info(f"更新工作流运行记录: {run_id}")

        return run

    @staticmethod
    async def finish_run(
        session: AsyncSession,
        run_id: str,
        status: str,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorkflowRun]:
        """完成运行记录"""
        # 使用 naive datetime（无时区），与数据库字段类型一致
        ended_at = datetime.utcnow()

        # 计算运行时长
        run = await WorkflowRunDAO.get_by_id(session, run_id)
        duration = None
        if run and run.started_at:
            # 确保两个datetime都是naive，避免时区问题
            started_at = run.started_at
            if started_at.tzinfo is not None:
                started_at = started_at.replace(tzinfo=None)
            duration = int((ended_at - started_at).total_seconds() / 60)

        update_data = {
            "status": status,
            "ended_at": ended_at,
            "duration": duration,
            "error_message": error_message,
        }

        if additional_data:
            update_data.update(additional_data)

        return await WorkflowRunDAO.update(session, run_id, update_data)


class ModelRegistryDAO:
    """模型注册表 DAO"""

    @staticmethod
    async def create(
        session: AsyncSession, model_data: Dict[str, Any]
    ) -> ModelRegistry:
        model = ModelRegistry(**model_data)
        session.add(model)
        await session.commit()
        await session.refresh(model)
        logger.info("注册模型: %s (%s)", model.name, model.model_type)
        return model

    @staticmethod
    async def get_by_id(
        session: AsyncSession, model_id: str
    ) -> Optional[ModelRegistry]:
        result = await session.execute(
            select(ModelRegistry).where(ModelRegistry.id == model_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_models(
        session: AsyncSession,
        *,
        model_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ModelRegistry]:
        query = select(ModelRegistry)
        if model_type:
            query = query.where(ModelRegistry.model_type == model_type)
        if status:
            query = query.where(ModelRegistry.status == status)
        query = query.order_by(ModelRegistry.created_at.desc())
        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update(
        session: AsyncSession, model_id: str, update_data: Dict[str, Any]
    ) -> Optional[ModelRegistry]:
        update_data["updated_at"] = datetime.utcnow()
        result = await session.execute(
            update(ModelRegistry)
            .where(ModelRegistry.id == model_id)
            .values(**update_data)
            .returning(ModelRegistry)
        )
        model = result.scalar_one_or_none()
        if model:
            await session.commit()
            logger.info("更新模型信息: %s", model_id)
        return model

    @staticmethod
    async def delete(session: AsyncSession, model_id: str) -> bool:
        result = await session.execute(
            delete(ModelRegistry).where(ModelRegistry.id == model_id)
        )
        await session.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info("删除模型记录: %s", model_id)
        return deleted
