"""
MLflow集成模块 - 实验追踪和模型版本管理

核心功能：
1. 实验追踪 - 记录训练参数、指标和模型
2. 模型版本管理 - 自动版本化和模型注册
3. 性能监控 - 记录模型性能指标
4. 实验比较 - 比较不同实验的结果
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    import mlflow
    import mlflow.pytorch
    import mlflow.sklearn
    import mlflow.tensorflow
    from mlflow.entities import RunStatus
    from mlflow.tracking import MlflowClient

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None
    MlflowClient = None
    RunStatus = None

logger = logging.getLogger(__name__)


class MLflowIntegration:
    """MLflow集成类"""

    def __init__(
        self,
        experiment_name: str = "human_behavior_detection",
        tracking_uri: Optional[str] = None,
        registry_uri: Optional[str] = None,
        enable_auto_logging: bool = True,
    ):
        """
        初始化MLflow集成

        Args:
            experiment_name: 实验名称
            tracking_uri: MLflow跟踪URI
            registry_uri: 模型注册URI
            enable_auto_logging: 是否启用自动日志记录
        """
        if not MLFLOW_AVAILABLE:
            raise ImportError("MLflow未安装，请运行: pip install mlflow")

        self.experiment_name = experiment_name
        self.enable_auto_logging = enable_auto_logging

        # 设置MLflow配置
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        if registry_uri:
            mlflow.set_registry_uri(registry_uri)

        # 创建或获取实验
        try:
            self.experiment_id = mlflow.create_experiment(experiment_name)
            logger.info(f"创建新实验: {experiment_name} (ID: {self.experiment_id})")
        except mlflow.exceptions.MlflowException:
            self.experiment_id = mlflow.get_experiment_by_name(
                experiment_name
            ).experiment_id
            logger.info(f"使用现有实验: {experiment_name} (ID: {self.experiment_id})")

        # 初始化客户端
        self.client = MlflowClient()

        # 当前运行
        self.current_run = None

        logger.info("MLflow集成初始化完成")

    def start_run(
        self,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
    ) -> str:
        """
        开始新的运行

        Args:
            run_name: 运行名称
            tags: 标签
            description: 描述

        Returns:
            str: 运行ID
        """
        if self.current_run is not None:
            logger.warning("已有运行在进行中，将结束当前运行")
            self.end_run()

        # 设置默认标签
        default_tags = {
            "project": "human_behavior_detection",
            "framework": "pytorch",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if tags:
            default_tags.update(tags)

        # 开始运行
        self.current_run = mlflow.start_run(
            experiment_id=self.experiment_id,
            run_name=run_name,
            tags=default_tags,
            description=description,
        )

        logger.info(f"开始新运行: {self.current_run.info.run_id}")
        return self.current_run.info.run_id

    def end_run(self, status: str = "FINISHED"):
        """结束当前运行"""
        if self.current_run is None:
            logger.warning("没有正在进行的运行")
            return

        try:
            mlflow.end_run(status=status)
            logger.info(f"运行已结束: {self.current_run.info.run_id}")
        except Exception as e:
            logger.error(f"结束运行失败: {e}")
        finally:
            self.current_run = None

    def log_parameters(self, params: Dict[str, Any]):
        """记录参数"""
        if self.current_run is None:
            logger.warning("没有正在进行的运行，无法记录参数")
            return

        try:
            mlflow.log_params(params)
            logger.debug(f"已记录参数: {list(params.keys())}")
        except Exception as e:
            logger.error(f"记录参数失败: {e}")

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """记录指标"""
        if self.current_run is None:
            logger.warning("没有正在进行的运行，无法记录指标")
            return

        try:
            mlflow.log_metrics(metrics, step=step)
            logger.debug(f"已记录指标: {list(metrics.keys())}")
        except Exception as e:
            logger.error(f"记录指标失败: {e}")

    def log_model(
        self,
        model,
        model_name: str,
        model_type: str = "pytorch",
        artifacts: Optional[Dict[str, str]] = None,
        registered_model_name: Optional[str] = None,
    ):
        """
        记录模型

        Args:
            model: 模型对象
            model_name: 模型名称
            model_type: 模型类型 (pytorch, sklearn, tensorflow)
            artifacts: 附加文件
            registered_model_name: 注册模型名称
        """
        if self.current_run is None:
            logger.warning("没有正在进行的运行，无法记录模型")
            return

        try:
            if model_type == "pytorch":
                mlflow.pytorch.log_model(
                    model, model_name, registered_model_name=registered_model_name
                )
            elif model_type == "sklearn":
                mlflow.sklearn.log_model(
                    model, model_name, registered_model_name=registered_model_name
                )
            elif model_type == "tensorflow":
                mlflow.tensorflow.log_model(
                    model, model_name, registered_model_name=registered_model_name
                )
            else:
                raise ValueError(f"不支持的模型类型: {model_type}")

            # 记录附加文件
            if artifacts:
                for artifact_name, artifact_path in artifacts.items():
                    mlflow.log_artifact(artifact_path, artifact_name)

            logger.info(f"已记录模型: {model_name} ({model_type})")
        except Exception as e:
            logger.error(f"记录模型失败: {e}")

    def log_artifacts(self, artifacts_dir: str, artifact_path: Optional[str] = None):
        """记录文件"""
        if self.current_run is None:
            logger.warning("没有正在进行的运行，无法记录文件")
            return

        try:
            mlflow.log_artifacts(artifacts_dir, artifact_path)
            logger.info(f"已记录文件: {artifacts_dir}")
        except Exception as e:
            logger.error(f"记录文件失败: {e}")

    def log_image(self, image, name: str, description: Optional[str] = None):
        """记录图像"""
        if self.current_run is None:
            logger.warning("没有正在进行的运行，无法记录图像")
            return

        try:
            mlflow.log_image(image, name)
            if description:
                mlflow.log_text(description, f"{name}_description.txt")
            logger.debug(f"已记录图像: {name}")
        except Exception as e:
            logger.error(f"记录图像失败: {e}")

    def log_detection_results(
        self, results: Dict[str, Any], frame_info: Optional[Dict[str, Any]] = None
    ):
        """
        记录检测结果

        Args:
            results: 检测结果
            frame_info: 帧信息
        """
        if self.current_run is None:
            logger.warning("没有正在进行的运行，无法记录检测结果")
            return

        try:
            # 记录检测指标
            detection_metrics = {
                "person_count": len(results.get("person_detections", [])),
                "hairnet_count": len(results.get("hairnet_results", [])),
                "handwash_count": len(results.get("handwash_results", [])),
                "sanitize_count": len(results.get("sanitize_results", [])),
                "processing_time": results.get("processing_time", 0.0),
                "fps": results.get("fps", 0.0),
            }

            # 计算准确率指标
            if "accuracy" in results:
                detection_metrics["accuracy"] = results["accuracy"]
            if "precision" in results:
                detection_metrics["precision"] = results["precision"]
            if "recall" in results:
                detection_metrics["recall"] = results["recall"]
            if "f1_score" in results:
                detection_metrics["f1_score"] = results["f1_score"]

            self.log_metrics(detection_metrics)

            # 记录帧信息
            if frame_info:
                frame_metrics = {
                    "frame_width": frame_info.get("width", 0),
                    "frame_height": frame_info.get("height", 0),
                    "frame_number": frame_info.get("frame_number", 0),
                    "timestamp": frame_info.get("timestamp", 0.0),
                }
                self.log_metrics(frame_metrics)

            logger.debug("已记录检测结果")
        except Exception as e:
            logger.error(f"记录检测结果失败: {e}")

    def log_performance_metrics(self, performance_data: Dict[str, Any]):
        """记录性能指标"""
        if self.current_run is None:
            logger.warning("没有正在进行的运行，无法记录性能指标")
            return

        try:
            # 提取性能指标
            perf_metrics = {}
            for key, value in performance_data.items():
                if isinstance(value, (int, float)):
                    perf_metrics[key] = value
                elif isinstance(value, dict) and "avg" in value:
                    perf_metrics[f"{key}_avg"] = value["avg"]
                    if "min" in value:
                        perf_metrics[f"{key}_min"] = value["min"]
                    if "max" in value:
                        perf_metrics[f"{key}_max"] = value["max"]

            self.log_metrics(perf_metrics)
            logger.debug("已记录性能指标")
        except Exception as e:
            logger.error(f"记录性能指标失败: {e}")

    def get_experiment_runs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取实验运行列表"""
        try:
            runs = self.client.search_runs(
                experiment_ids=[self.experiment_id], max_results=limit
            )

            run_list = []
            for run in runs:
                run_info = {
                    "run_id": run.info.run_id,
                    "run_name": run.data.tags.get("mlflow.runName", ""),
                    "status": run.info.status,
                    "start_time": run.info.start_time,
                    "end_time": run.info.end_time,
                    "metrics": run.data.metrics,
                    "params": run.data.params,
                    "tags": run.data.tags,
                }
                run_list.append(run_info)

            return run_list
        except Exception as e:
            logger.error(f"获取实验运行失败: {e}")
            return []

    def compare_runs(self, run_ids: List[str]) -> pd.DataFrame:
        """比较运行结果"""
        try:
            runs = []
            for run_id in run_ids:
                run = self.client.get_run(run_id)
                run_data = {
                    "run_id": run_id,
                    "run_name": run.data.tags.get("mlflow.runName", ""),
                    **run.data.metrics,
                    **run.data.params,
                }
                runs.append(run_data)

            return pd.DataFrame(runs)
        except Exception as e:
            logger.error(f"比较运行失败: {e}")
            return pd.DataFrame()

    def register_model(
        self,
        model_name: str,
        model_version: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        注册模型

        Args:
            model_name: 模型名称
            model_version: 模型版本
            description: 描述
            tags: 标签

        Returns:
            str: 模型版本
        """
        if self.current_run is None:
            raise ValueError("没有正在进行的运行，无法注册模型")

        try:
            # 创建注册模型
            try:
                self.client.create_registered_model(model_name, description)
            except mlflow.exceptions.MlflowException:
                pass  # 模型已存在

            # 注册模型版本
            model_uri = f"runs:/{self.current_run.info.run_id}/model"
            model_version = self.client.create_model_version(
                name=model_name,
                source=model_uri,
                run_id=self.current_run.info.run_id,
                description=description,
                tags=tags,
            )

            logger.info(f"模型已注册: {model_name} v{model_version.version}")
            return model_version.version
        except Exception as e:
            logger.error(f"注册模型失败: {e}")
            raise

    def get_model_versions(self, model_name: str) -> List[Dict[str, Any]]:
        """获取模型版本列表"""
        try:
            versions = self.client.get_latest_versions(model_name)
            version_list = []
            for version in versions:
                version_info = {
                    "version": version.version,
                    "stage": version.current_stage,
                    "creation_timestamp": version.creation_timestamp,
                    "last_updated_timestamp": version.last_updated_timestamp,
                    "description": version.description,
                    "tags": version.tags,
                }
                version_list.append(version_info)
            return version_list
        except Exception as e:
            logger.error(f"获取模型版本失败: {e}")
            return []

    def promote_model(self, model_name: str, version: str, stage: str):
        """提升模型阶段"""
        try:
            self.client.transition_model_version_stage(
                name=model_name, version=version, stage=stage
            )
            logger.info(f"模型 {model_name} v{version} 已提升到 {stage} 阶段")
        except Exception as e:
            logger.error(f"提升模型阶段失败: {e}")

    def export_experiment(self, output_dir: str):
        """导出实验数据"""
        try:
            os.makedirs(output_dir, exist_ok=True)

            # 导出运行数据
            runs = self.get_experiment_runs()
            with open(
                os.path.join(output_dir, "runs.json"), "w", encoding="utf-8"
            ) as f:
                json.dump(runs, f, indent=2, ensure_ascii=False, default=str)

            # 导出实验配置
            experiment_config = {
                "experiment_name": self.experiment_name,
                "experiment_id": self.experiment_id,
                "total_runs": len(runs),
                "export_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open(
                os.path.join(output_dir, "experiment_config.json"),
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(experiment_config, f, indent=2, ensure_ascii=False)

            logger.info(f"实验数据已导出到: {output_dir}")
        except Exception as e:
            logger.error(f"导出实验数据失败: {e}")

    def cleanup_old_runs(self, keep_last_n: int = 50):
        """清理旧运行"""
        try:
            runs = self.get_experiment_runs(limit=1000)
            if len(runs) <= keep_last_n:
                return

            # 按开始时间排序，删除最旧的运行
            runs.sort(key=lambda x: x["start_time"], reverse=True)
            runs_to_delete = runs[keep_last_n:]

            for run in runs_to_delete:
                try:
                    self.client.delete_run(run["run_id"])
                    logger.debug(f"已删除运行: {run['run_id']}")
                except Exception as e:
                    logger.warning(f"删除运行失败 {run['run_id']}: {e}")

            logger.info(f"已清理 {len(runs_to_delete)} 个旧运行")
        except Exception as e:
            logger.error(f"清理旧运行失败: {e}")

    def get_experiment_summary(self) -> Dict[str, Any]:
        """获取实验摘要"""
        try:
            runs = self.get_experiment_runs()

            if not runs:
                return {"error": "没有找到运行数据"}

            # 统计信息
            total_runs = len(runs)
            successful_runs = len([r for r in runs if r["status"] == "FINISHED"])
            failed_runs = len([r for r in runs if r["status"] == "FAILED"])

            # 最近运行
            recent_runs = sorted(runs, key=lambda x: x["start_time"], reverse=True)[:5]

            # 常用指标
            common_metrics = set()
            for run in runs:
                common_metrics.update(run["metrics"].keys())

            summary = {
                "experiment_name": self.experiment_name,
                "experiment_id": self.experiment_id,
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "success_rate": successful_runs / total_runs if total_runs > 0 else 0,
                "recent_runs": recent_runs,
                "common_metrics": list(common_metrics),
            }

            return summary
        except Exception as e:
            logger.error(f"获取实验摘要失败: {e}")
            return {"error": str(e)}
