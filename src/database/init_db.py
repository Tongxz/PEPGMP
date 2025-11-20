"""
数据库初始化脚本
创建数据库表并插入初始数据
"""

import asyncio
import logging
from datetime import datetime
from src.database.connection import init_database, get_async_session
from src.database.dao import DatasetDAO, DeploymentDAO, WorkflowDAO, WorkflowRunDAO

logger = logging.getLogger(__name__)


async def create_initial_data():
    """创建初始数据"""
    async for session in get_async_session():
        try:
            # 创建示例数据集
            datasets = [
                {
                    "id": "dataset_001",
                    "name": "handwash_detection_v1",
                    "version": "1.0.0",
                    "status": "active",
                    "size": 1024 * 1024 * 500,  # 500MB
                    "sample_count": 1500,
                    "label_count": 3,
                    "quality_score": 85.0,
                    "quality_metrics": {
                        "completeness": 92.0,
                        "accuracy": 88.0,
                        "consistency": 85.0
                    },
                    "description": "洗手行为检测数据集",
                    "tags": ["handwash", "detection", "behavior"],
                    "file_path": "data/datasets/handwash_detection_v1"
                },
                {
                    "id": "dataset_002",
                    "name": "hairnet_detection_v2",
                    "version": "2.1.0",
                    "status": "active",
                    "size": 1024 * 1024 * 300,  # 300MB
                    "sample_count": 800,
                    "label_count": 2,
                    "quality_score": 92.0,
                    "quality_metrics": {
                        "completeness": 95.0,
                        "accuracy": 90.0,
                        "consistency": 92.0
                    },
                    "description": "安全帽检测数据集",
                    "tags": ["hairnet", "detection", "safety"],
                    "file_path": "data/datasets/hairnet_detection_v2"
                }
            ]
            
            for dataset_data in datasets:
                # 检查数据集是否已存在
                existing = await DatasetDAO.get_by_id(session, dataset_data["id"])
                if existing:
                    logger.info(f"数据集 {dataset_data['id']} 已存在，跳过创建")
                else:
                    await DatasetDAO.create(session, dataset_data)
            
            # 创建示例部署
            deployments = [
                {
                    "id": "deployment_001",
                    "name": "human-detection-prod",
                    "model_version": "yolo_human_v1.0",
                    "environment": "production",
                    "status": "running",
                    "replicas": 3,
                    "cpu_limit": "2",
                    "memory_limit": "4Gi",
                    "gpu_count": 1,
                    "gpu_memory": "8Gi",
                    "auto_scaling": True,
                    "min_replicas": 2,
                    "max_replicas": 10,
                    "update_strategy": "rolling",
                    "cpu_usage": 65.0,
                    "memory_usage": 78.0,
                    "gpu_usage": 45.0,
                    "requests_per_minute": 1200,
                    "avg_response_time": 45.0,
                    "error_rate": 0.5,
                    "total_requests": 172800,
                    "success_rate": 99.5,
                    "deployment_config": {
                        "image": "pyt-api:latest",
                        "ports": [{"containerPort": 8000, "protocol": "TCP"}],
                        "env": [
                            {"name": "MODEL_PATH", "value": "/app/models/yolo_human.pt"},
                            {"name": "DEVICE", "value": "cuda"}
                        ]
                    }
                },
                {
                    "id": "deployment_002",
                    "name": "hairnet-detection-staging",
                    "model_version": "yolo_hairnet_v2.1",
                    "environment": "staging",
                    "status": "running",
                    "replicas": 1,
                    "cpu_limit": "1",
                    "memory_limit": "2Gi",
                    "gpu_count": 0,
                    "auto_scaling": False,
                    "cpu_usage": 45.0,
                    "memory_usage": 60.0,
                    "requests_per_minute": 300,
                    "avg_response_time": 35.0,
                    "error_rate": 1.2,
                    "total_requests": 43200,
                    "success_rate": 98.8,
                    "deployment_config": {
                        "image": "pyt-api:latest",
                        "ports": [{"containerPort": 8000, "protocol": "TCP"}],
                        "env": [
                            {"name": "MODEL_PATH", "value": "/app/models/yolo_hairnet.pt"},
                            {"name": "DEVICE", "value": "cpu"}
                        ]
                    }
                }
            ]
            
            for deployment_data in deployments:
                # 检查部署是否已存在
                existing = await DeploymentDAO.get_by_id(session, deployment_data["id"])
                if existing:
                    logger.info(f"部署 {deployment_data['id']} 已存在，跳过创建")
                else:
                    await DeploymentDAO.create(session, deployment_data)
            
            # 创建示例工作流
            workflows = [
                {
                    "id": "workflow_001",
                    "name": "智能检测模型训练流水线",
                    "type": "training",
                    "status": "active",
                    "trigger": "schedule",
                    "schedule": "0 2 * * *",
                    "description": "每日自动训练智能检测模型",
                    "steps": [
                        {
                            "name": "数据预处理",
                            "type": "data_processing",
                            "description": "清洗和预处理检测数据",
                            "config": "{}"
                        },
                        {
                            "name": "模型训练",
                            "type": "model_training",
                            "description": "训练YOLOv8检测模型",
                            "config": "{}"
                        },
                        {
                            "name": "模型评估",
                            "type": "model_evaluation",
                            "description": "评估模型性能",
                            "config": "{}"
                        },
                        {
                            "name": "模型部署",
                            "type": "model_deployment",
                            "description": "部署到生产环境",
                            "config": "{}"
                        }
                    ],
                    "run_count": 15,
                    "success_rate": 93.3,
                    "avg_duration": 45.0,
                    "last_run": datetime.utcnow(),
                    "workflow_config": {
                        "timeout": 3600,
                        "retry_count": 3,
                        "notifications": {
                            "on_success": True,
                            "on_failure": True
                        }
                    }
                },
                {
                    "id": "workflow_002",
                    "name": "模型性能评估流水线",
                    "type": "evaluation",
                    "status": "active",
                    "trigger": "webhook",
                    "description": "当新模型部署时自动评估性能",
                    "steps": [
                        {
                            "name": "数据验证",
                            "type": "data_validation",
                            "description": "验证测试数据质量",
                            "config": "{}"
                        },
                        {
                            "name": "模型评估",
                            "type": "model_evaluation",
                            "description": "评估模型性能指标",
                            "config": "{}"
                        },
                        {
                            "name": "报告生成",
                            "type": "notification",
                            "description": "生成评估报告",
                            "config": "{}"
                        }
                    ],
                    "run_count": 8,
                    "success_rate": 100.0,
                    "avg_duration": 12.0,
                    "last_run": datetime.utcnow(),
                    "workflow_config": {
                        "timeout": 1800,
                        "retry_count": 2
                    }
                }
            ]
            
            for workflow_data in workflows:
                # 检查工作流是否已存在
                existing = await WorkflowDAO.get_by_id(session, workflow_data["id"])
                if existing:
                    logger.info(f"工作流 {workflow_data['id']} 已存在，跳过创建")
                else:
                    await WorkflowDAO.create(session, workflow_data)
            
            # 创建示例运行记录
            runs = [
                {
                    "id": "run_001",
                    "workflow_id": "workflow_001",
                    "status": "success",
                    "started_at": datetime.utcnow(),
                    "ended_at": datetime.utcnow(),
                    "duration": 42,
                    "run_config": {"trigger": "schedule", "version": "1.0.0"}
                },
                {
                    "id": "run_002",
                    "workflow_id": "workflow_001",
                    "status": "success",
                    "started_at": datetime.utcnow(),
                    "ended_at": datetime.utcnow(),
                    "duration": 38,
                    "run_config": {"trigger": "schedule", "version": "1.0.0"}
                },
                {
                    "id": "run_003",
                    "workflow_id": "workflow_002",
                    "status": "success",
                    "started_at": datetime.utcnow(),
                    "ended_at": datetime.utcnow(),
                    "duration": 11,
                    "run_config": {"trigger": "webhook", "deployment_id": "deployment_001"}
                }
            ]
            
            for run_data in runs:
                # 检查运行记录是否已存在
                existing = await WorkflowRunDAO.get_by_id(session, run_data["id"])
                if existing:
                    logger.info(f"运行记录 {run_data['id']} 已存在，跳过创建")
                else:
                    await WorkflowRunDAO.create(session, run_data)
            
            logger.info("初始数据创建完成")
            break  # 退出生成器循环
            
        except Exception as e:
            logger.error(f"创建初始数据失败: {e}")
            raise


async def main():
    """主函数"""
    try:
        # 初始化数据库
        await init_database()
        
        # 创建初始数据
        await create_initial_data()
        
        print("数据库初始化完成！")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
