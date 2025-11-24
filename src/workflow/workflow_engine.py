"""
工作流引擎
提供工作流的执行、调度、监控功能
"""

import asyncio
import json
import logging
import threading
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from src.application.dataset_generation_service import (
    DatasetGenerationRequest,
    DatasetGenerationService,
)
from src.application.handwash_dataset_generation_service import (
    HandwashDatasetGenerationService,
    HandwashDatasetRequest,
)
from src.application.handwash_training_service import HandwashTrainingService
from src.application.model_training_service import ModelTrainingService
from src.application.multi_behavior_dataset_service import (
    MultiBehaviorDatasetGenerationService,
    MultiBehaviorDatasetRequest,
)
from src.application.multi_behavior_training_service import MultiBehaviorTrainingService
from src.container.service_container import get_service
from src.database.connection import AsyncSessionLocal

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """工作流状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(Enum):
    """步骤类型枚举"""

    DATA_PROCESSING = "data_processing"
    DATASET_GENERATION = "dataset_generation"
    HANDWASH_DATASET = "handwash_dataset"
    MODEL_TRAINING = "model_training"
    HANDWASH_TRAINING = "handwash_training"
    MULTI_BEHAVIOR_DATASET = "multi_behavior_dataset"
    MULTI_BEHAVIOR_TRAINING = "multi_behavior_training"
    MODEL_EVALUATION = "model_evaluation"
    MODEL_DEPLOYMENT = "model_deployment"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


class WorkflowEngine:
    """工作流引擎"""

    def __init__(self):
        self.running_workflows: Dict[str, asyncio.Task] = {}
        self.scheduled_workflows: Dict[str, asyncio.Task] = {}
        # 用于取消训练任务的取消事件字典
        self.cancel_events: Dict[str, threading.Event] = {}
        self.step_handlers: Dict[StepType, Callable] = {
            StepType.DATA_PROCESSING: self._handle_data_processing,
            StepType.DATASET_GENERATION: self._handle_dataset_generation,
            StepType.HANDWASH_DATASET: self._handle_handwash_dataset_generation,
            StepType.MULTI_BEHAVIOR_DATASET: self._handle_multi_behavior_dataset_generation,
            StepType.MODEL_TRAINING: self._handle_model_training,
            StepType.HANDWASH_TRAINING: self._handle_handwash_training,
            StepType.MULTI_BEHAVIOR_TRAINING: self._handle_multi_behavior_training,
            StepType.MODEL_EVALUATION: self._handle_model_evaluation,
            StepType.MODEL_DEPLOYMENT: self._handle_model_deployment,
            StepType.NOTIFICATION: self._handle_notification,
            StepType.CUSTOM: self._handle_custom_step,
        }

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                logger.warning("无法解析时间字符串: %s", value)
                return None
        return None

    async def create_workflow(self, workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建工作流

        Args:
            workflow_config: 工作流配置

        Returns:
            创建结果
        """
        try:
            workflow_id = workflow_config.get("id")
            name = workflow_config.get("name")
            trigger = workflow_config.get("trigger", "manual")

            logger.info(f"创建工作流: {name} (ID: {workflow_id})")

            # 验证工作流配置
            validation_result = self._validate_workflow_config(workflow_config)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "message": f"工作流配置验证失败: {validation_result['error']}",
                }

            # 根据触发器类型处理
            if trigger == "schedule":
                # 调度工作流
                schedule_result = await self._schedule_workflow(workflow_config)
                if schedule_result["success"]:
                    logger.info(f"✅ 工作流调度成功: {name}")
                    return {
                        "success": True,
                        "workflow_id": workflow_id,
                        "status": "scheduled",
                        "message": f"工作流 {name} 调度成功",
                    }
                else:
                    return {
                        "success": False,
                        "error": schedule_result["error"],
                        "message": f"工作流调度失败: {schedule_result['error']}",
                    }
            else:
                # 手动触发工作流
                logger.info(f"✅ 工作流创建成功: {name}")
                return {
                    "success": True,
                    "workflow_id": workflow_id,
                    "status": "created",
                    "message": f"工作流 {name} 创建成功",
                }

        except Exception as e:
            logger.error(f"创建工作流异常: {e}")
            return {"success": False, "error": str(e), "message": "工作流创建异常"}

    async def run_workflow(
        self, workflow_id: str, workflow_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        运行工作流

        Args:
            workflow_id: 工作流ID
            workflow_config: 工作流配置

        Returns:
            运行结果
        """
        try:
            logger.info(f"[工作流引擎] 开始运行工作流: workflow_id={workflow_id}")

            # 检查是否已在运行
            if workflow_id in self.running_workflows:
                logger.warning(f"[工作流引擎] 工作流已在运行中: workflow_id={workflow_id}")
                return {
                    "success": False,
                    "error": "工作流正在运行中",
                    "message": f"工作流 {workflow_id} 正在运行中",
                }

            run_id = f"run_{int(datetime.utcnow().timestamp())}"
            logger.info(
                f"[工作流引擎] 创建工作流运行任务: workflow_id={workflow_id}, run_id={run_id}"
            )

            # 创建取消事件
            cancel_event = threading.Event()
            self.cancel_events[workflow_id] = cancel_event

            # 创建任务来执行工作流，这样才能正确取消
            task = asyncio.create_task(
                self._execute_workflow(
                    workflow_id, run_id, workflow_config, cancel_event
                )
            )
            self.running_workflows[workflow_id] = task

            # 等待任务完成
            result = await task

            # 任务完成后从运行列表中移除
            if workflow_id in self.running_workflows:
                del self.running_workflows[workflow_id]

            return result

        except asyncio.CancelledError:
            logger.info(f"工作流 {workflow_id} 已被取消")
            # 从运行列表中移除
            if workflow_id in self.running_workflows:
                del self.running_workflows[workflow_id]
            return {
                "success": False,
                "error": "工作流已取消",
                "message": f"工作流 {workflow_id} 已被取消",
            }
        except Exception as e:
            logger.error(f"运行工作流异常: {e}")
            # 从运行列表中移除
            if workflow_id in self.running_workflows:
                del self.running_workflows[workflow_id]
            return {"success": False, "error": str(e), "message": "工作流运行异常"}

    async def stop_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        停止工作流

        Args:
            workflow_id: 工作流ID

        Returns:
            停止结果
        """
        try:
            stopped = False

            # 首先设置取消事件，通知训练任务停止（即使工作流不在运行列表中）
            if workflow_id in self.cancel_events:
                cancel_event = self.cancel_events[workflow_id]
                cancel_event.set()
                logger.info(f"已设置取消事件: {workflow_id}")
                stopped = True

            # 如果工作流在运行列表中，取消运行任务
            if workflow_id in self.running_workflows:
                task = self.running_workflows[workflow_id]
                try:
                    task.cancel()
                    logger.info(f"已取消工作流任务: {workflow_id}")
                    stopped = True
                except Exception as e:
                    logger.warning(f"取消工作流任务失败: {e}")

                # 从运行列表中移除
                try:
                    del self.running_workflows[workflow_id]
                except KeyError:
                    pass  # 可能已经被删除

            # 如果工作流在调度列表中，也取消调度
            if workflow_id in self.scheduled_workflows:
                scheduled_task = self.scheduled_workflows[workflow_id]
                try:
                    scheduled_task.cancel()
                    logger.info(f"已取消调度工作流任务: {workflow_id}")
                    stopped = True
                except Exception as e:
                    logger.warning(f"取消调度工作流任务失败: {e}")

                # 从调度列表中移除
                try:
                    del self.scheduled_workflows[workflow_id]
                except KeyError:
                    pass  # 可能已经被删除

            if stopped:
                logger.info(f"✅ 工作流已停止: {workflow_id}")
                return {
                    "success": True,
                    "workflow_id": workflow_id,
                    "status": "cancelled",
                    "message": f"工作流 {workflow_id} 已停止",
                }
            else:
                # 即使没有找到运行中的任务，也尝试创建取消事件（以防训练任务还在运行）
                # 这样即使工作流不在运行列表中，训练任务也能响应取消
                if workflow_id not in self.cancel_events:
                    cancel_event = threading.Event()
                    cancel_event.set()  # 立即设置，因为要停止
                    self.cancel_events[workflow_id] = cancel_event
                    logger.info(f"为工作流 {workflow_id} 创建并设置取消事件（工作流不在运行列表中）")

                logger.info(f"工作流 {workflow_id} 未在运行列表中，但已设置取消事件")
                return {
                    "success": True,
                    "workflow_id": workflow_id,
                    "status": "cancelled",
                    "message": f"工作流 {workflow_id} 停止请求已发送",
                }

        except Exception as e:
            logger.error(f"停止工作流异常: {e}")
            return {"success": False, "error": str(e), "message": "工作流停止异常"}

    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        获取工作流状态

        Args:
            workflow_id: 工作流ID

        Returns:
            工作流状态
        """
        try:
            if workflow_id in self.running_workflows:
                task = self.running_workflows[workflow_id]
                if task.done():
                    # 任务已完成，从运行列表中移除
                    del self.running_workflows[workflow_id]
                    return {
                        "workflow_id": workflow_id,
                        "status": "completed",
                        "running": False,
                    }
                else:
                    return {
                        "workflow_id": workflow_id,
                        "status": "running",
                        "running": True,
                    }
            else:
                return {"workflow_id": workflow_id, "status": "idle", "running": False}

        except Exception as e:
            logger.error(f"获取工作流状态异常: {e}")
            return {
                "workflow_id": workflow_id,
                "status": "error",
                "running": False,
                "error": str(e),
            }

    async def _execute_workflow(
        self,
        workflow_id: str,
        run_id: str,
        workflow_config: Dict[str, Any],
        cancel_event: Optional[threading.Event] = None,
    ) -> Dict[str, Any]:
        """
        执行工作流

        Args:
            workflow_id: 工作流ID
            run_id: 运行ID
            workflow_config: 工作流配置

        Returns:
            执行结果
        """
        try:
            steps = workflow_config.get("steps", [])
            total_steps = len(steps)
            completed_steps = 0
            context: Dict[str, Any] = {"step_outputs": [], "last_output": None}

            logger.info(
                f"[工作流执行] 开始执行工作流: workflow_id={workflow_id}, total_steps={total_steps}, steps={[s.get('name', '') for s in steps]}"
            )

            for i, step in enumerate(steps):
                try:
                    # 检查是否被取消
                    current_task = asyncio.current_task()
                    if current_task and current_task.cancelled():
                        raise asyncio.CancelledError("工作流已被取消")

                    # 检查取消事件
                    if cancel_event and cancel_event.is_set():
                        logger.info(f"检测到取消事件，停止工作流: {workflow_id}")
                        raise asyncio.CancelledError("工作流已被取消")

                    step_name = step.get("name", f"步骤 {i+1}")
                    step_type = StepType(step.get("type", "custom"))

                    logger.info(
                        f"[工作流执行] 执行步骤 {i+1}/{total_steps}: step_name={step_name}, step_type={step_type.value}"
                    )

                    # 执行步骤，传递取消事件
                    step_result = await self._execute_step(
                        step_type,
                        step,
                        workflow_config,
                        context,
                        cancel_event,
                    )

                    if step_result["success"]:
                        completed_steps += 1
                        logger.info(f"✅ 步骤 {i+1} 执行成功: {step_name}")
                        context["last_output"] = step_result.get("output")
                        context["step_outputs"].append(
                            {
                                "name": step_name,
                                "type": step_type.value,
                                "output": step_result.get("output"),
                            }
                        )
                        if step_type == StepType.DATASET_GENERATION:
                            context["last_dataset_output"] = step_result.get("output")
                    else:
                        logger.error(
                            f"❌ 步骤 {i+1} 执行失败: {step_name} - {step_result.get('error')}"
                        )
                        return {
                            "success": False,
                            "workflow_id": workflow_id,
                            "run_id": run_id,
                            "completed_steps": completed_steps,
                            "total_steps": total_steps,
                            "failed_step": i + 1,
                            "error": step_result.get("error", "步骤执行失败"),
                        }

                except Exception as e:
                    logger.error(f"步骤 {i+1} 执行异常: {e}")
                    return {
                        "success": False,
                        "workflow_id": workflow_id,
                        "run_id": run_id,
                        "completed_steps": completed_steps,
                        "total_steps": total_steps,
                        "failed_step": i + 1,
                        "error": str(e),
                    }

            logger.info(
                f"✅ 工作流执行完成: {workflow_id} ({completed_steps}/{total_steps} 步骤)"
            )
            return {
                "success": True,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "completed_steps": completed_steps,
                "total_steps": total_steps,
                "message": "工作流执行完成",
                "outputs": context.get("step_outputs", []),
            }

        except asyncio.CancelledError:
            logger.info(f"工作流被取消: {workflow_id}")
            return {
                "success": False,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "cancelled": True,
                "error": "工作流被取消",
                "message": "工作流被取消",
            }
        except Exception as e:
            logger.error(f"工作流执行异常: {e}")
            return {
                "success": False,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "error": str(e),
                "message": "工作流执行异常",
            }
        finally:
            # 从运行列表中移除
            if workflow_id in self.running_workflows:
                del self.running_workflows[workflow_id]
            # 清理取消事件
            if workflow_id in self.cancel_events:
                del self.cancel_events[workflow_id]

    async def _execute_step(
        self,
        step_type: StepType,
        step_config: Dict[str, Any],
        workflow_config: Dict[str, Any],
        context: Dict[str, Any],
        cancel_event: Optional[threading.Event] = None,
    ) -> Dict[str, Any]:
        """
        执行单个步骤

        Args:
            step_type: 步骤类型
            step_config: 步骤配置
            workflow_config: 工作流配置

        Returns:
            步骤执行结果
        """
        try:
            handler = self.step_handlers.get(step_type)
            if not handler:
                return {"success": False, "error": f"不支持的步骤类型: {step_type}"}

            # 将取消事件传递给步骤处理器（通过 context）
            context_with_cancel = {**context, "_cancel_event": cancel_event}
            return await handler(step_config, workflow_config, context_with_cancel)

        except Exception as e:
            logger.error(f"步骤执行异常: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_data_processing(
        self,
        step_config: Dict[str, Any],
        workflow_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理数据预处理步骤"""
        try:
            # 模拟数据预处理
            await asyncio.sleep(2)  # 模拟处理时间

            logger.info("数据预处理步骤执行完成")
            return {
                "success": True,
                "message": "数据预处理完成",
                "output": {"processed_samples": 1000, "quality_score": 0.95},
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_dataset_generation(  # noqa: C901
        self,
        step_config: Dict[str, Any],
        workflow_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理数据集生成步骤"""

        def parse_datetime(value: Any) -> Optional[datetime]:
            if not value:
                return None
            if isinstance(value, datetime):
                return value
            if isinstance(value, (int, float)):
                timestamp = value / 1000 if value > 1e12 else value
                return datetime.fromtimestamp(timestamp)
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning("无法解析时间字符串: %s", value)
                    return None
            return None

        config_data = step_config.get("config") or {}
        if isinstance(config_data, str):
            try:
                config_data = json.loads(config_data)
            except json.JSONDecodeError:
                logger.warning("步骤配置解析失败: %s", config_data)
                config_data = {}

        dataset_params = step_config.get("dataset_params") or {}
        if isinstance(dataset_params, str):
            try:
                dataset_params = json.loads(dataset_params)
            except json.JSONDecodeError:
                logger.warning("dataset_params 解析失败: %s", dataset_params)
                dataset_params = {}

        merged_params = {**config_data, **dataset_params}

        dataset_name = (
            step_config.get("dataset_name")
            or merged_params.get("dataset_name")
            or f"{workflow_config.get('name', 'dataset')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )

        camera_ids = step_config.get("camera_ids") or merged_params.get("camera_ids")
        if isinstance(camera_ids, str):
            camera_ids = [cid.strip() for cid in camera_ids.split(",") if cid.strip()]
        elif isinstance(camera_ids, list):
            camera_ids = [str(cid).strip() for cid in camera_ids if str(cid).strip()]

        include_normal = bool(
            step_config.get(
                "include_normal_samples",
                merged_params.get("include_normal_samples", False),
            )
        )
        max_records = int(
            step_config.get("max_records", merged_params.get("max_records", 1000))
        )
        start_time = parse_datetime(
            step_config.get("start_time")
            or merged_params.get("start_time")
            or step_config.get("start_timestamp")
            or merged_params.get("start_timestamp")
        )
        end_time = parse_datetime(
            step_config.get("end_time")
            or merged_params.get("end_time")
            or step_config.get("end_timestamp")
            or merged_params.get("end_timestamp")
        )

        try:
            dataset_service = get_service(DatasetGenerationService)
        except Exception as exc:
            logger.error("获取数据集生成服务失败: %s", exc)
            return {"success": False, "error": "数据集生成服务不可用"}

        request = DatasetGenerationRequest(
            dataset_name=dataset_name,
            camera_ids=camera_ids,
            start_time=start_time,
            end_time=end_time,
            include_normal_samples=include_normal,
            max_records=max_records,
        )

        try:
            async with AsyncSessionLocal() as session:
                result = await dataset_service.generate_dataset(request, session)
            logger.info("数据集生成步骤执行完成: %s", result.get("dataset_id"))
            return {
                "success": True,
                "message": "数据集生成完成",
                "output": result,
            }
        except Exception as e:
            logger.error("数据集生成步骤失败: %s", e)
            return {"success": False, "error": str(e)}

    async def _handle_handwash_dataset_generation(
        self,
        step_config: Dict[str, Any],
        workflow_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理洗手数据集生成步骤"""

        def parse_datetime(value: Any) -> Optional[datetime]:
            if not value:
                return None
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning("无法解析时间字符串: %s", value)
                    return None
            return None

        try:
            service = get_service(HandwashDatasetGenerationService)
        except Exception as exc:
            logger.error("获取洗手数据集服务失败: %s", exc)
            return {"success": False, "error": "洗手数据集服务不可用"}

        config = step_config.get("config") or {}
        dataset_name = config.get("dataset_name") or (
            workflow_config.get("name", "handwash_dataset")
            + f"_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )

        request = HandwashDatasetRequest(
            dataset_name=dataset_name,
            start_time=parse_datetime(config.get("start_time")),
            end_time=parse_datetime(config.get("end_time")),
            camera_ids=config.get("camera_ids"),
            max_sessions=config.get("max_sessions"),
            frame_interval=config.get("frame_interval"),
        )

        try:
            async with AsyncSessionLocal() as db_session:
                result = await service.generate_dataset(request, db_session)
            context["last_handwash_dataset"] = result
            logger.info(
                "洗手数据集生成完成: %s (samples=%s)",
                result.get("dataset_name"),
                result.get("samples"),
            )
            return {
                "success": True,
                "message": "洗手数据集生成完成",
                "output": result,
            }
        except Exception as exc:
            logger.error("洗手数据集生成失败: %s", exc)
            return {"success": False, "error": str(exc)}

    async def _handle_multi_behavior_dataset_generation(
        self,
        step_config: Dict[str, Any],
        workflow_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理多行为数据集生成步骤"""
        try:
            service = get_service(MultiBehaviorDatasetGenerationService)
        except Exception as exc:
            logger.error("获取多行为数据集服务失败: %s", exc)
            return {"success": False, "error": "多行为数据集服务不可用"}

        config = step_config.get("config") or {}
        dataset_name = config.get("dataset_name") or (
            workflow_config.get("name", "multibeh_dataset")
            + f"_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )

        request = MultiBehaviorDatasetRequest(
            dataset_name=dataset_name,
            violation_types=config.get("violation_types"),
            start_time=self._parse_datetime(config.get("start_time")),
            end_time=self._parse_datetime(config.get("end_time")),
            camera_ids=config.get("camera_ids"),
            max_records=config.get("max_records"),
        )

        try:
            async with AsyncSessionLocal() as db_session:
                result = await service.generate_dataset(request, db_session)
            context["last_multi_behavior_dataset"] = result
            logger.info(
                "多行为数据集生成完成: %s (samples=%s)",
                result.get("dataset_name"),
                result.get("samples"),
            )
            return {
                "success": True,
                "message": "多行为数据集生成完成",
                "output": result,
            }
        except Exception as exc:
            logger.error("多行为数据集生成失败: %s", exc)
            return {"success": False, "error": str(exc)}

    async def _handle_model_training(
        self,
        step_config: Dict[str, Any],
        workflow_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理模型训练步骤"""
        try:
            dataset_output = context.get("last_dataset_output") or {}
            dataset_path = step_config.get("dataset_path") or dataset_output.get(
                "dataset_path"
            )
            annotations_path = step_config.get(
                "annotations_path"
            ) or dataset_output.get("annotations_path")

            if not dataset_path:
                raise ValueError("模型训练步骤未提供数据集路径，且未找到上一步的数据集输出")

            try:
                training_service = get_service(ModelTrainingService)
            except Exception as exc:
                logger.error("获取模型训练服务失败: %s", exc)
                return {"success": False, "error": "模型训练服务不可用"}

            training_params: Dict[str, Any] = {}
            config_data = step_config.get("config")
            if isinstance(config_data, dict):
                training_params.update(config_data)
            if isinstance(step_config.get("training_params"), dict):
                training_params.update(step_config["training_params"])

            result = await training_service.train_from_dataset(
                Path(dataset_path),
                annotations_file=Path(annotations_path) if annotations_path else None,
                training_params=training_params,
                dataset_metadata=dataset_output,
            )

            logger.info(
                "模型训练完成: samples=%s, accuracy=%s",
                result.samples_used,
                result.metrics.get("accuracy"),
            )
            return {
                "success": True,
                "message": "模型训练完成",
                "output": {
                    "model_path": str(result.model_path),
                    "report_path": str(result.report_path),
                    "metrics": result.metrics,
                    "samples_used": result.samples_used,
                    "version": result.version,
                    "artifacts": result.artifacts,
                },
            }
        except Exception as e:
            logger.error("模型训练步骤失败: %s", e)
            return {"success": False, "error": str(e)}

    async def _handle_handwash_training(
        self,
        step_config: Dict[str, Any],
        workflow_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理洗手训练步骤"""
        try:
            training_service = get_service(HandwashTrainingService)
        except Exception as exc:
            logger.error("获取洗手训练服务失败: %s", exc)
            return {"success": False, "error": "洗手训练服务不可用"}

        config = step_config.get("config") or {}
        dataset_dir = config.get("dataset_dir")
        annotations_file = config.get("annotations_file")

        last_dataset = context.get("last_handwash_dataset") or context.get(
            "last_dataset_output"
        )
        if not dataset_dir and last_dataset:
            dataset_dir = last_dataset.get("dataset_path")
        if not annotations_file and last_dataset:
            annotations_file = last_dataset.get("annotations_path")

        if not dataset_dir:
            return {"success": False, "error": "未提供洗手训练数据集目录"}

        training_params = config.get("training_params", {})
        try:
            result = await training_service.train(
                Path(dataset_dir),
                annotations_file=Path(annotations_file) if annotations_file else None,
                training_params=training_params,
                dataset_metadata=last_dataset,
            )
            output = {
                "model_path": str(result.model_path),
                "report_path": str(result.report_path),
                "metrics": result.metrics,
                "samples_used": result.samples_used,
                "version": result.version,
                "artifacts": result.artifacts,
            }
            context["last_handwash_training"] = output
            logger.info("洗手训练完成: %s", result.model_path)
            return {"success": True, "message": "洗手训练完成", "output": output}
        except Exception as exc:
            logger.error("洗手训练步骤失败: %s", exc)
            return {"success": False, "error": str(exc)}

    async def _handle_multi_behavior_training(
        self,
        step_config: Dict[str, Any],
        workflow_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理多行为训练步骤"""
        try:
            training_service = get_service(MultiBehaviorTrainingService)
        except Exception as exc:
            logger.error("获取多行为训练服务失败: %s", exc)
            return {"success": False, "error": "多行为训练服务不可用"}

        config = step_config.get("config") or {}
        dataset_dir = config.get("dataset_dir")
        data_config = config.get("data_config")

        last_dataset = context.get("last_multi_behavior_dataset") or context.get(
            "last_dataset_output"
        )
        if not dataset_dir and last_dataset:
            dataset_dir = last_dataset.get("dataset_path")
        if not data_config and last_dataset:
            data_config = last_dataset.get("yaml_path")

        if not dataset_dir:
            return {"success": False, "error": "未提供多行为训练数据集目录"}

        training_params = config.get("training_params", {})

        # 检查是否要从上一次训练结果继续训练
        # 1. 优先使用训练参数中明确指定的 resume_from
        # 2. 如果没有指定，检查 context 中是否有上一次训练的模型路径
        if "resume_from" not in training_params and "from_model" not in training_params:
            last_training = context.get("last_multi_behavior_training") or context.get(
                "last_training_output"
            )
            if last_training and last_training.get("model_path"):
                resume_model_path = last_training.get("model_path")
                training_params["resume_from"] = resume_model_path
                logger.info(f"[工作流执行] 自动使用上一次训练的模型继续训练: {resume_model_path}")

        # 从 context 中获取取消事件
        cancel_event = context.get("_cancel_event")
        if cancel_event:
            # 将取消事件传递给训练服务
            training_params["_cancel_event"] = cancel_event

        logger.info(
            f"[工作流执行] 开始多行为训练: dataset_dir={dataset_dir}, data_config={data_config}"
        )
        try:
            result = await training_service.train(
                Path(dataset_dir),
                data_config=Path(data_config) if data_config else None,
                training_params=training_params,
                dataset_metadata=last_dataset,
            )
            output = {
                "model_path": str(result.model_path),
                "report_path": str(result.report_path),
                "metrics": result.metrics,
                "samples_used": result.samples_used,
                "version": result.version,
                "artifacts": result.artifacts,
            }
            # 保存训练结果到 context，供后续步骤使用（如继续训练）
            context["last_multi_behavior_training"] = output
            context["last_training_output"] = output  # 通用键名，供其他步骤使用
            logger.info(
                f"[工作流执行] 多行为训练完成: model_path={result.model_path}, metrics={result.metrics}"
            )
            return {"success": True, "message": "多行为训练完成", "output": output}
        except Exception as exc:
            logger.error("多行为训练步骤失败: %s", exc)
            return {"success": False, "error": str(exc)}

    async def _handle_model_evaluation(
        self,
        step_config: Dict[str, Any],
        workflow_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理模型评估步骤"""
        try:
            # 模拟模型评估
            await asyncio.sleep(3)  # 模拟评估时间

            logger.info("模型评估步骤执行完成")
            return {
                "success": True,
                "message": "模型评估完成",
                "output": {
                    "accuracy": 0.92,
                    "precision": 0.89,
                    "recall": 0.91,
                    "f1_score": 0.90,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_model_deployment(
        self,
        step_config: Dict[str, Any],
        workflow_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理模型部署步骤"""
        try:
            from src.domain.interfaces.deployment_interface import IDeploymentService

            # 获取部署服务（使用已导入的 get_service）
            try:
                deployment_service = get_service(IDeploymentService)
            except ValueError as exc:
                logger.error("获取部署服务失败: %s", exc)
                return {"success": False, "error": f"部署服务不可用: {exc}"}
            except Exception as exc:
                logger.error("获取部署服务失败: %s", exc, exc_info=True)
                return {"success": False, "error": f"部署服务不可用: {exc}"}

            # 准备部署配置
            deployment_config = step_config.get("config", {})
            # 如果有上一步训练的模型路径，自动填充
            last_training = (
                context.get("last_training_output")
                or context.get("last_multi_behavior_training")
                or context.get("last_handwash_training")
            )

            if last_training and last_training.get("model_path"):
                if "model_path" not in deployment_config:
                    deployment_config["model_path"] = last_training["model_path"]
                    logger.info(f"自动使用上一步训练的模型: {deployment_config['model_path']}")

            # 执行部署
            deployment_id = await deployment_service.create_deployment(
                deployment_config
            )
            logger.info(f"[模型部署] 部署ID: {deployment_id}")

            # 获取状态
            status = await deployment_service.get_deployment_status(deployment_id)

            # 检查部署状态
            if status.status == "not_found":
                # 容器不存在时，记录警告但允许工作流继续
                # 这可能是因为容器尚未创建，或者部署只是更新配置
                logger.warning(f"[模型部署] 容器 {deployment_id} 不存在，但部署步骤完成（可能仅更新配置）")
                return {
                    "success": True,  # 改为成功，因为配置更新可能已完成
                    "message": f"部署配置已更新（容器 {deployment_id} 不存在，可能需要手动创建）",
                    "output": {
                        "deployment_id": deployment_id,
                        "status": status.status,
                        "warning": f"容器不存在: {deployment_id}",
                        "note": "部署配置已更新，但容器不存在。如果这是新部署，请手动创建容器。",
                    },
                }
            elif status.status == "error" and status.error:
                # 只有在有明确错误时才失败
                logger.error(f"[模型部署] 部署状态异常: {status.error}")
                return {
                    "success": False,
                    "error": f"部署状态异常: {status.error}",
                    "output": {
                        "deployment_id": deployment_id,
                        "status": status.status,
                        "error": status.error,
                    },
                }
            elif status.status in ["stopped", "created"]:
                # 容器已停止或已创建但未启动，记录警告但允许继续
                logger.warning(f"[模型部署] 容器 {deployment_id} 状态为 {status.status}，可能需要启动")
                return {
                    "success": True,
                    "message": f"部署完成，但容器状态为 {status.status}",
                    "output": {
                        "deployment_id": deployment_id,
                        "status": status.status,
                        "replicas": status.replicas,
                        "warning": f"容器状态为 {status.status}，可能需要启动",
                    },
                }

            logger.info(f"[模型部署] 部署步骤执行完成: {deployment_id}, 状态: {status.status}")
            return {
                "success": True,
                "message": "模型部署完成",
                "output": {
                    "deployment_id": deployment_id,
                    "status": status.status,
                    "replicas": status.replicas,
                    "cpu_usage": status.cpu_usage,
                    "memory_usage": status.memory_usage,
                },
            }
        except Exception as e:
            logger.error(f"模型部署步骤失败: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_notification(
        self,
        step_config: Dict[str, Any],
        workflow_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理通知步骤"""
        try:
            # 模拟发送通知
            await asyncio.sleep(1)  # 模拟通知时间

            logger.info("通知步骤执行完成")
            return {
                "success": True,
                "message": "通知发送完成",
                "output": {
                    "notification_sent": True,
                    "recipients": ["admin@example.com"],
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_custom_step(
        self,
        step_config: Dict[str, Any],
        workflow_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理自定义步骤"""
        try:
            # 模拟自定义步骤
            await asyncio.sleep(2)  # 模拟处理时间

            logger.info("自定义步骤执行完成")
            return {
                "success": True,
                "message": "自定义步骤完成",
                "output": {"custom_result": "success"},
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _validate_workflow_config(
        self, workflow_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证工作流配置

        Args:
            workflow_config: 工作流配置

        Returns:
            验证结果
        """
        try:
            # 检查必需字段
            required_fields = ["id", "name", "steps"]
            for field in required_fields:
                if field not in workflow_config:
                    return {"valid": False, "error": f"缺少必需字段: {field}"}

            # 检查步骤配置
            steps = workflow_config.get("steps", [])
            if not steps:
                return {"valid": False, "error": "工作流必须包含至少一个步骤"}

            for i, step in enumerate(steps):
                if "name" not in step or "type" not in step:
                    return {"valid": False, "error": f"步骤 {i+1} 缺少必需字段: name 或 type"}

                # 验证步骤类型
                try:
                    StepType(step["type"])
                except ValueError:
                    return {
                        "valid": False,
                        "error": f"步骤 {i+1} 包含无效的类型: {step['type']}",
                    }

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": f"配置验证异常: {str(e)}"}

    async def recover_state(self):
        """
        恢复工作流状态（自愈机制）
        检查数据库中状态为 running 但内存中不存在的任务，将其标记为 failed
        """
        from src.database.dao import WorkflowRunDAO

        logger.info("[工作流引擎] 开始执行状态自愈检查...")

        try:
            async with AsyncSessionLocal() as session:
                # 1. 获取所有数据库中状态为 running 的记录
                running_runs = await WorkflowRunDAO.get_running_runs(session)

                for run in running_runs:
                    # 2. 检查是否在内存中
                    workflow_id = run.workflow_id
                    if workflow_id not in self.running_workflows:
                        logger.warning(
                            f"[自愈] 发现僵尸任务: run_id={run.id}, workflow_id={workflow_id}。正在修复..."
                        )

                        # 3. 修复状态
                        try:
                            await WorkflowRunDAO.finish_run(
                                session,
                                run.id,
                                "failed",
                                "服务异常重启导致任务中断",
                                additional_data={
                                    "run_log": json.dumps(
                                        {"recovery": "auto_healed_at_startup"},
                                        ensure_ascii=False,
                                    )
                                },
                            )

                            # 更新工作流主表状态（如果需要）
                            # 注意：这里假设 WorkflowRunDAO 已经处理了关联逻辑，如果没有，可能需要单独更新 Workflow 表

                            logger.info(f"[自愈] 任务 {run.id} 已标记为失败")
                        except Exception as update_error:
                            logger.error(f"[自愈] 修复任务 {run.id} 失败: {update_error}")

        except Exception as e:
            logger.error(f"[自愈] 状态检查失败: {e}")

    async def _schedule_workflow(
        self, workflow_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调度工作流

        Args:
            workflow_config: 工作流配置

        Returns:
            调度结果
        """
        try:
            # 这里可以实现基于cron的调度
            # 目前只是简单返回成功
            logger.info(f"工作流调度成功: {workflow_config.get('name')}")
            return {"success": True}

        except Exception as e:
            logger.error(f"工作流调度异常: {e}")
            return {"success": False, "error": str(e)}


# 全局工作流引擎实例
workflow_engine = WorkflowEngine()
