"""
创建工作流脚本：基于之前训练的模型继续训练
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import AsyncSessionLocal
from src.database.dao import WorkflowDAO
from src.workflow.workflow_engine import workflow_engine


async def create_resume_training_workflow():
    """创建基于之前训练模型继续训练的工作流"""
    
    # 模型路径（使用相对路径，相对于项目根目录）
    model_path = "models/multi_behavior/multi_behavior_20251117_153832.pt"
    
    # 数据集路径（根据实际情况调整）
    dataset_dir = "data/datasets/hairnet.v15i.yolov8"
    data_config = "data/datasets/hairnet.v15i.yolov8/data.yaml"
    
    # 验证模型文件是否存在
    model_file = Path(project_root / model_path)
    if not model_file.exists():
        print(f"[ERROR] 模型文件不存在: {model_file}")
        print(f"   请检查模型路径是否正确")
        return
    
    print(f"[OK] 模型文件存在: {model_file}")
    
    # 验证数据集路径
    dataset_path = Path(project_root / dataset_dir)
    data_config_path = Path(project_root / data_config)
    
    if not dataset_path.exists():
        print(f"[WARNING] 数据集目录不存在: {dataset_path}")
        print(f"   请确认数据集路径是否正确")
    
    if not data_config_path.exists():
        print(f"[WARNING] 数据配置文件不存在: {data_config_path}")
        print(f"   请确认数据配置路径是否正确")
    
    # 创建工作流配置
    workflow_config = {
        "name": "发网检测继续训练",
        "type": "training",
        "status": "active",
        "trigger": "manual",
        "description": f"基于模型 {model_path} 继续训练，提高模型性能",
        "steps": [
            {
                "name": "数据预处理",
                "type": "multi_behavior_training",
                "description": f"从模型 {model_path} 继续训练",
                "config": {
                    "dataset_dir": dataset_dir,
                    "data_config": data_config,
                    "training_params": {
                        "resume_from": model_path,  # 指定继续训练的模型路径
                        "epochs": 30,  # 继续训练30轮
                        "batch_size": 16,
                        "image_size": 640,
                        "device": "auto",
                        "lr0": 0.001,  # 继续训练时使用较小的学习率
                        "lrf": 0.01
                    }
                }
            }
        ]
    }
    
    print("\n" + "=" * 60)
    print("工作流配置:")
    print("=" * 60)
    print(json.dumps(workflow_config, indent=2, ensure_ascii=False))
    print("=" * 60 + "\n")
    
    # 创建数据库会话
    async with AsyncSessionLocal() as session:
        try:
            # 生成工作流ID
            import time
            workflow_id = f"workflow_{int(time.time())}"
            workflow_config["id"] = workflow_id
            
            # 设置默认值
            workflow_config.setdefault("run_count", 0)
            workflow_config.setdefault("success_rate", 0.0)
            workflow_config.setdefault("avg_duration", 0.0)
            
            # 保存到数据库
            workflow_obj = await WorkflowDAO.create(session, workflow_config)
            print(f"[OK] 数据库记录创建成功: {workflow_obj.id}")
            
            # 创建工作流引擎实例
            engine_result = await workflow_engine.create_workflow(workflow_config)
            
            if engine_result.get("success"):
                # 更新数据库状态
                await WorkflowDAO.update(
                    session,
                    workflow_id,
                    {"status": "active", "workflow_config": engine_result},
                )
                
                print(f"[OK] 工作流创建成功!")
                print(f"   工作流ID: {workflow_obj.id}")
                print(f"   工作流名称: {workflow_obj.name}")
                print(f"   状态: active")
                print(f"\n   现在可以通过以下方式运行工作流:")
                print(f"   1. 前端界面: 在工作流管理页面点击'运行'按钮")
                print(f"   2. API调用: POST /api/v1/mlops/workflows/{workflow_obj.id}/run")
                return workflow_obj.id
            else:
                # 更新数据库状态为失败
                await WorkflowDAO.update(
                    session,
                    workflow_id,
                    {
                        "status": "error",
                        "workflow_config": {"error": engine_result.get("error", "未知错误")},
                    },
                )
                
                print(f"[ERROR] 工作流引擎创建失败: {engine_result.get('error')}")
                return None
                
        except Exception as e:
            print(f"[ERROR] 创建工作流失败: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    print("=" * 60)
    print("创建继续训练工作流")
    print("=" * 60)
    print()
    
    workflow_id = asyncio.run(create_resume_training_workflow())
    
    if workflow_id:
        print(f"\n[OK] 工作流创建完成!")
    else:
        print(f"\n[ERROR] 工作流创建失败!")
        sys.exit(1)

