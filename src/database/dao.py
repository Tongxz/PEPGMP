"""
数据访问层 (DAO)
提供数据集、部署、工作流等实体的CRUD操作
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from src.database.models import Dataset, Deployment, Workflow, WorkflowRun

logger = logging.getLogger(__name__)


class DatasetDAO:
    """数据集数据访问对象"""
    
    @staticmethod
    async def create(session: AsyncSession, dataset_data: Dict[str, Any]) -> Dataset:
        """创建数据集"""
        dataset = Dataset(**dataset_data)
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
        offset: int = 0
    ) -> List[Dataset]:
        """获取所有数据集"""
        query = select(Dataset)
        
        if status:
            query = query.where(Dataset.status == status)
        
        query = query.offset(offset).limit(limit).order_by(Dataset.created_at.desc())
        
        result = await session.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def update(session: AsyncSession, dataset_id: str, update_data: Dict[str, Any]) -> Optional[Dataset]:
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
    async def create(session: AsyncSession, deployment_data: Dict[str, Any]) -> Deployment:
        """创建部署"""
        deployment = Deployment(**deployment_data)
        session.add(deployment)
        await session.commit()
        await session.refresh(deployment)
        logger.info(f"创建部署: {deployment.id}")
        return deployment
    
    @staticmethod
    async def get_by_id(session: AsyncSession, deployment_id: str) -> Optional[Deployment]:
        """根据ID获取部署"""
        result = await session.execute(select(Deployment).where(Deployment.id == deployment_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all(session: AsyncSession) -> List[Deployment]:
        """获取所有部署"""
        result = await session.execute(select(Deployment).order_by(Deployment.created_at.desc()))
        return result.scalars().all()
    
    @staticmethod
    async def update(session: AsyncSession, deployment_id: str, update_data: Dict[str, Any]) -> Optional[Deployment]:
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
        result = await session.execute(delete(Deployment).where(Deployment.id == deployment_id))
        await session.commit()
        
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"删除部署: {deployment_id}")
        
        return deleted
    
    @staticmethod
    async def update_metrics(session: AsyncSession, deployment_id: str, metrics: Dict[str, Any]) -> Optional[Deployment]:
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
        result = await session.execute(select(Workflow).where(Workflow.id == workflow_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all(session: AsyncSession) -> List[Workflow]:
        """获取所有工作流"""
        result = await session.execute(select(Workflow).order_by(Workflow.created_at.desc()))
        return result.scalars().all()
    
    @staticmethod
    async def update(session: AsyncSession, workflow_id: str, update_data: Dict[str, Any]) -> Optional[Workflow]:
        """更新工作流"""
        update_data["updated_at"] = datetime.utcnow()
        
        result = await session.execute(
            update(Workflow)
            .where(Workflow.id == workflow_id)
            .values(**update_data)
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
        await session.execute(delete(WorkflowRun).where(WorkflowRun.workflow_id == workflow_id))
        
        # 再删除工作流
        result = await session.execute(delete(Workflow).where(Workflow.id == workflow_id))
        await session.commit()
        
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"删除工作流: {workflow_id}")
        
        return deleted
    
    @staticmethod
    async def get_with_recent_runs(session: AsyncSession, workflow_id: str, limit: int = 5) -> Optional[Workflow]:
        """获取工作流及其最近运行记录"""
        # 获取工作流
        workflow_result = await session.execute(select(Workflow).where(Workflow.id == workflow_id))
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
        run = WorkflowRun(**run_data)
        session.add(run)
        await session.commit()
        await session.refresh(run)
        logger.info(f"创建工作流运行记录: {run.id}")
        return run
    
    @staticmethod
    async def get_by_id(session: AsyncSession, run_id: str) -> Optional[WorkflowRun]:
        """根据ID获取运行记录"""
        result = await session.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_workflow_id(session: AsyncSession, workflow_id: str, limit: int = 10) -> List[WorkflowRun]:
        """根据工作流ID获取运行记录"""
        result = await session.execute(
            select(WorkflowRun)
            .where(WorkflowRun.workflow_id == workflow_id)
            .order_by(WorkflowRun.started_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def update(session: AsyncSession, run_id: str, update_data: Dict[str, Any]) -> Optional[WorkflowRun]:
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
    async def finish_run(session: AsyncSession, run_id: str, status: str, error_message: Optional[str] = None) -> Optional[WorkflowRun]:
        """完成运行记录"""
        ended_at = datetime.utcnow()
        
        # 计算运行时长
        run = await WorkflowRunDAO.get_by_id(session, run_id)
        duration = None
        if run and run.started_at:
            duration = int((ended_at - run.started_at).total_seconds() / 60)
        
        update_data = {
            "status": status,
            "ended_at": ended_at,
            "duration": duration,
            "error_message": error_message
        }
        
        return await WorkflowRunDAO.update(session, run_id, update_data)
