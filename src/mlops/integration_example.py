"""
MLOps集成示例 - 展示如何在检测系统中集成MLflow和DVC

核心功能：
1. 实验追踪 - 记录检测实验和模型训练
2. 数据版本管理 - 管理数据集和模型版本
3. 性能监控 - 记录和比较模型性能
4. 自动化流程 - 集成到检测流程中
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

from .dvc_integration import DVCIntegration
from .mlflow_integration import MLflowIntegration

logger = logging.getLogger(__name__)


class MLOpsIntegration:
    """MLOps集成类"""

    def __init__(
        self,
        experiment_name: str = "human_behavior_detection",
        repo_path: str = ".",
        mlflow_tracking_uri: Optional[str] = None,
        dvc_remote: Optional[str] = None,
    ):
        """
        初始化MLOps集成

        Args:
            experiment_name: 实验名称
            repo_path: 仓库路径
            mlflow_tracking_uri: MLflow跟踪URI
            dvc_remote: DVC远程存储
        """
        self.experiment_name = experiment_name
        self.repo_path = repo_path

        # 初始化MLflow
        try:
            self.mlflow = MLflowIntegration(
                experiment_name=experiment_name, tracking_uri=mlflow_tracking_uri
            )
            self.mlflow_available = True
        except ImportError:
            logger.warning("MLflow不可用，实验追踪功能将被禁用")
            self.mlflow = None
            self.mlflow_available = False

        # 初始化DVC
        try:
            self.dvc = DVCIntegration(repo_path=repo_path, dvc_remote=dvc_remote)
            self.dvc_available = self.dvc.dvc_initialized
        except Exception as e:
            logger.warning(f"DVC不可用: {e}")
            self.dvc = None
            self.dvc_available = False

        logger.info(
            f"MLOps集成初始化完成 - MLflow: {self.mlflow_available}, DVC: {self.dvc_available}"
        )

    def start_detection_experiment(
        self,
        run_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
    ) -> Optional[str]:
        """
        开始检测实验

        Args:
            run_name: 运行名称
            config: 配置参数
            description: 描述

        Returns:
            Optional[str]: 运行ID
        """
        if not self.mlflow_available:
            logger.warning("MLflow不可用，无法开始实验")
            return None

        try:
            # 开始MLflow运行
            run_id = self.mlflow.start_run(
                run_name=run_name or f"detection_{int(time.time())}",
                description=description,
                tags={"type": "detection", "system": "intelligent_detection"},
            )

            # 记录配置参数
            if config:
                self.mlflow.log_parameters(config)

            # 记录系统信息
            system_info = {
                "python_version": os.sys.version,
                "platform": os.name,
                "working_directory": os.getcwd(),
                "experiment_name": self.experiment_name,
            }
            self.mlflow.log_parameters(system_info)

            logger.info(f"检测实验已开始: {run_id}")
            return run_id
        except Exception as e:
            logger.error(f"开始检测实验失败: {e}")
            return None

    def log_detection_metrics(
        self, metrics: Dict[str, float], step: Optional[int] = None
    ):
        """记录检测指标"""
        if not self.mlflow_available:
            return

        try:
            self.mlflow.log_metrics(metrics, step=step)
            logger.debug(f"已记录检测指标: {list(metrics.keys())}")
        except Exception as e:
            logger.error(f"记录检测指标失败: {e}")

    def log_model_performance(
        self,
        model_name: str,
        performance_data: Dict[str, Any],
        model_path: Optional[str] = None,
    ):
        """
        记录模型性能

        Args:
            model_name: 模型名称
            performance_data: 性能数据
            model_path: 模型路径
        """
        if not self.mlflow_available:
            return

        try:
            # 记录性能指标
            self.mlflow.log_performance_metrics(performance_data)

            # 记录模型（如果提供了路径）
            if model_path and os.path.exists(model_path):
                self.mlflow.log_model(
                    model=model_path,
                    model_name=model_name,
                    model_type="pytorch",
                    artifacts={"performance_report": "performance_report.json"},
                )

            logger.info(f"模型性能已记录: {model_name}")
        except Exception as e:
            logger.error(f"记录模型性能失败: {e}")

    def track_dataset(
        self,
        dataset_path: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        quality_thresholds: Optional[Dict[str, float]] = None,
    ) -> bool:
        """
        跟踪数据集

        Args:
            dataset_path: 数据集路径
            description: 描述
            tags: 标签
            quality_thresholds: 质量阈值

        Returns:
            bool: 是否成功
        """
        if not self.dvc_available:
            logger.warning("DVC不可用，无法跟踪数据集")
            return False

        try:
            # 跟踪数据集
            if os.path.isfile(dataset_path):
                success = self.dvc.track_file(dataset_path, description, tags)
            else:
                success = self.dvc.track_directory(
                    dataset_path, description=description, tags=tags
                )

            if success:
                # 跟踪数据质量
                if quality_thresholds:
                    self.dvc.track_data_quality(dataset_path, quality_thresholds)

                logger.info(f"数据集已跟踪: {dataset_path}")

            return success
        except Exception as e:
            logger.error(f"跟踪数据集失败: {e}")
            return False

    def commit_experiment(self, message: str, push_data: bool = True) -> bool:
        """
        提交实验

        Args:
            message: 提交消息
            push_data: 是否推送数据

        Returns:
            bool: 是否成功
        """
        success = True

        # 结束MLflow运行
        if self.mlflow_available:
            try:
                self.mlflow.end_run()
                logger.info("MLflow运行已结束")
            except Exception as e:
                logger.error(f"结束MLflow运行失败: {e}")
                success = False

        # 提交DVC更改
        if self.dvc_available:
            try:
                self.dvc.commit_changes(message)
                if push_data:
                    self.dvc.push_data()
                logger.info("DVC更改已提交")
            except Exception as e:
                logger.error(f"提交DVC更改失败: {e}")
                success = False

        return success

    def get_experiment_summary(self) -> Dict[str, Any]:
        """获取实验摘要"""
        summary = {
            "mlflow_available": self.mlflow_available,
            "dvc_available": self.dvc_available,
            "experiment_name": self.experiment_name,
        }

        if self.mlflow_available:
            try:
                mlflow_summary = self.mlflow.get_experiment_summary()
                summary["mlflow"] = mlflow_summary
            except Exception as e:
                summary["mlflow_error"] = str(e)

        if self.dvc_available:
            try:
                # 获取跟踪的文件
                summary["dvc"] = {
                    "tracked_files": list(self.dvc.tracked_files),
                    "data_metrics_count": len(self.dvc.data_metrics),
                }
            except Exception as e:
                summary["dvc_error"] = str(e)

        return summary

    def compare_experiments(
        self, run_ids: List[str], output_file: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        比较实验

        Args:
            run_ids: 运行ID列表
            output_file: 输出文件路径

        Returns:
            Optional[Dict[str, Any]]: 比较结果
        """
        if not self.mlflow_available:
            logger.warning("MLflow不可用，无法比较实验")
            return None

        try:
            # 获取比较结果
            comparison_df = self.mlflow.compare_runs(run_ids)

            # 生成比较报告
            comparison_report = {
                "run_ids": run_ids,
                "comparison_data": comparison_df.to_dict("records"),
                "summary": {
                    "total_runs": len(run_ids),
                    "common_metrics": list(comparison_df.columns),
                    "best_performance": self._find_best_performance(comparison_df),
                },
            }

            # 保存报告
            if output_file:
                import json

                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(
                        comparison_report, f, indent=2, ensure_ascii=False, default=str
                    )
                logger.info(f"比较报告已保存: {output_file}")

            return comparison_report
        except Exception as e:
            logger.error(f"比较实验失败: {e}")
            return None

    def _find_best_performance(self, comparison_df) -> Dict[str, Any]:
        """查找最佳性能"""
        best_performance = {}

        # 查找数值指标的最佳值
        numeric_cols = comparison_df.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            if (
                "accuracy" in col.lower()
                or "f1" in col.lower()
                or "precision" in col.lower()
                or "recall" in col.lower()
            ):
                # 这些指标越高越好
                best_idx = comparison_df[col].idxmax()
                best_performance[col] = {
                    "value": comparison_df.loc[best_idx, col],
                    "run_id": comparison_df.loc[best_idx, "run_id"],
                }
            elif "loss" in col.lower() or "error" in col.lower():
                # 这些指标越低越好
                best_idx = comparison_df[col].idxmin()
                best_performance[col] = {
                    "value": comparison_df.loc[best_idx, col],
                    "run_id": comparison_df.loc[best_idx, "run_id"],
                }

        return best_performance

    def export_experiment_data(
        self, output_dir: str, include_models: bool = True, include_data: bool = True
    ):
        """导出实验数据"""
        try:
            os.makedirs(output_dir, exist_ok=True)

            # 导出MLflow数据
            if self.mlflow_available and include_models:
                mlflow_dir = os.path.join(output_dir, "mlflow")
                self.mlflow.export_experiment(mlflow_dir)

            # 导出DVC数据
            if self.dvc_available and include_data:
                dvc_catalog = os.path.join(output_dir, "dvc_catalog.json")
                self.dvc.export_data_catalog(dvc_catalog)

            # 导出综合报告
            summary = self.get_experiment_summary()
            summary_file = os.path.join(output_dir, "experiment_summary.json")
            import json

            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"实验数据已导出: {output_dir}")
        except Exception as e:
            logger.error(f"导出实验数据失败: {e}")

    def cleanup_old_experiments(self, keep_last_n: int = 50):
        """清理旧实验"""
        if self.mlflow_available:
            try:
                self.mlflow.cleanup_old_runs(keep_last_n)
                logger.info(f"已清理旧实验，保留最近 {keep_last_n} 个")
            except Exception as e:
                logger.error(f"清理旧实验失败: {e}")


def create_mlops_integration(
    experiment_name: str = "human_behavior_detection",
    repo_path: str = ".",
    config: Optional[Dict[str, Any]] = None,
) -> MLOpsIntegration:
    """
    创建MLOps集成实例

    Args:
        experiment_name: 实验名称
        repo_path: 仓库路径
        config: 配置参数

    Returns:
        MLOpsIntegration: MLOps集成实例
    """
    # 默认配置
    default_config = {"mlflow_tracking_uri": None, "dvc_remote": None}

    if config:
        default_config.update(config)

    return MLOpsIntegration(
        experiment_name=experiment_name,
        repo_path=repo_path,
        mlflow_tracking_uri=default_config.get("mlflow_tracking_uri"),
        dvc_remote=default_config.get("dvc_remote"),
    )


# 使用示例
if __name__ == "__main__":
    # 创建MLOps集成
    mlops = create_mlops_integration(
        experiment_name="test_detection",
        config={"mlflow_tracking_uri": "file:///tmp/mlflow", "dvc_remote": "local"},
    )

    # 开始实验
    run_id = mlops.start_detection_experiment(
        run_name="test_run",
        config={"model_type": "yolov8", "input_size": 640, "confidence_threshold": 0.5},
        description="测试检测实验",
    )

    if run_id:
        # 记录一些指标
        mlops.log_detection_metrics(
            {"accuracy": 0.95, "fps": 15.2, "processing_time": 0.066}
        )

        # 跟踪数据集
        mlops.track_dataset(
            dataset_path="data/training",
            description="训练数据集",
            tags=["training", "detection"],
            quality_thresholds={"null_count": 0.1, "duplicate_count": 0.05},
        )

        # 提交实验
        mlops.commit_experiment("测试实验提交")

        # 获取摘要
        summary = mlops.get_experiment_summary()
        print("实验摘要:", summary)

    print("MLOps集成示例完成")
