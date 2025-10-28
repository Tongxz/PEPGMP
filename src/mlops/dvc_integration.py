"""
DVC集成模块 - 数据集版本管理

核心功能：
1. 数据集版本控制 - 跟踪数据集变化
2. 数据管道管理 - 自动化数据处理流程
3. 数据血缘追踪 - 追踪数据来源和转换
4. 数据质量监控 - 监控数据质量指标
"""

import hashlib
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DVCIntegration:
    """DVC集成类"""

    def __init__(
        self,
        repo_path: str = ".",
        dvc_remote: Optional[str] = None,
        enable_auto_tracking: bool = True,
    ):
        """
        初始化DVC集成

        Args:
            repo_path: 仓库路径
            dvc_remote: DVC远程存储
            enable_auto_tracking: 是否启用自动跟踪
        """
        self.repo_path = Path(repo_path).resolve()
        self.dvc_remote = dvc_remote
        self.enable_auto_tracking = enable_auto_tracking

        # 检查DVC是否已初始化
        self.dvc_initialized = self._check_dvc_init()

        if not self.dvc_initialized:
            logger.warning("DVC未初始化，某些功能可能不可用")

        # 数据跟踪配置
        self.tracked_files = set()
        self.data_metrics = {}

        logger.info(f"DVC集成初始化完成: {self.repo_path}")

    def _check_dvc_init(self) -> bool:
        """检查DVC是否已初始化"""
        try:
            result = subprocess.run(
                ["dvc", "version"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def init_dvc(self, force: bool = False) -> bool:
        """初始化DVC"""
        if self.dvc_initialized and not force:
            logger.info("DVC已初始化")
            return True

        try:
            subprocess.run(["dvc", "init"], cwd=self.repo_path, check=True)
            self.dvc_initialized = True
            logger.info("DVC初始化成功")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"DVC初始化失败: {e}")
            return False

    def add_remote(self, name: str, url: str, force: bool = False) -> bool:
        """添加远程存储"""
        if not self.dvc_initialized:
            logger.error("DVC未初始化，无法添加远程存储")
            return False

        try:
            cmd = ["dvc", "remote", "add", name, url]
            if force:
                cmd.append("--force")

            subprocess.run(cmd, cwd=self.repo_path, check=True)
            logger.info(f"远程存储已添加: {name} -> {url}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"添加远程存储失败: {e}")
            return False

    def track_file(
        self,
        file_path: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        跟踪文件

        Args:
            file_path: 文件路径
            description: 描述
            tags: 标签

        Returns:
            bool: 是否成功
        """
        if not self.dvc_initialized:
            logger.error("DVC未初始化，无法跟踪文件")
            return False

        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"文件不存在: {file_path}")
            return False

        try:
            # 添加文件到DVC
            subprocess.run(
                ["dvc", "add", str(file_path)], cwd=self.repo_path, check=True
            )

            # 记录跟踪信息
            self.tracked_files.add(str(file_path))

            # 添加描述和标签
            if description or tags:
                self._add_file_metadata(file_path, description, tags)

            logger.info(f"文件已跟踪: {file_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"跟踪文件失败: {e}")
            return False

    def track_directory(
        self,
        dir_path: str,
        pattern: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        跟踪目录

        Args:
            dir_path: 目录路径
            pattern: 文件模式
            description: 描述
            tags: 标签

        Returns:
            bool: 是否成功
        """
        if not self.dvc_initialized:
            logger.error("DVC未初始化，无法跟踪目录")
            return False

        dir_path = Path(dir_path)
        if not dir_path.exists() or not dir_path.is_dir():
            logger.error(f"目录不存在: {dir_path}")
            return False

        try:
            # 添加目录到DVC
            cmd = ["dvc", "add", str(dir_path)]
            if pattern:
                cmd.extend(["--glob", pattern])

            subprocess.run(cmd, cwd=self.repo_path, check=True)

            # 记录跟踪信息
            self.tracked_files.add(str(dir_path))

            # 添加描述和标签
            if description or tags:
                self._add_file_metadata(dir_path, description, tags)

            logger.info(f"目录已跟踪: {dir_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"跟踪目录失败: {e}")
            return False

    def _add_file_metadata(
        self,
        file_path: Path,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """添加文件元数据"""
        try:
            metadata = {
                "description": description,
                "tags": tags or [],
                "tracked_at": pd.Timestamp.now().isoformat(),
            }

            metadata_file = file_path.with_suffix(file_path.suffix + ".meta")
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            # 也跟踪元数据文件
            subprocess.run(
                ["dvc", "add", str(metadata_file)], cwd=self.repo_path, check=True
            )
        except Exception as e:
            logger.warning(f"添加文件元数据失败: {e}")

    def commit_changes(self, message: str) -> bool:
        """提交更改"""
        if not self.dvc_initialized:
            logger.error("DVC未初始化，无法提交更改")
            return False

        try:
            # 添加所有更改
            subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)

            # 提交更改
            subprocess.run(
                ["git", "commit", "-m", message], cwd=self.repo_path, check=True
            )

            logger.info(f"更改已提交: {message}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"提交更改失败: {e}")
            return False

    def push_data(self, remote: Optional[str] = None) -> bool:
        """推送数据到远程存储"""
        if not self.dvc_initialized:
            logger.error("DVC未初始化，无法推送数据")
            return False

        try:
            cmd = ["dvc", "push"]
            if remote:
                cmd.extend(["--remote", remote])

            subprocess.run(cmd, cwd=self.repo_path, check=True)
            logger.info("数据已推送到远程存储")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"推送数据失败: {e}")
            return False

    def pull_data(self, remote: Optional[str] = None) -> bool:
        """从远程存储拉取数据"""
        if not self.dvc_initialized:
            logger.error("DVC未初始化，无法拉取数据")
            return False

        try:
            cmd = ["dvc", "pull"]
            if remote:
                cmd.extend(["--remote", remote])

            subprocess.run(cmd, cwd=self.repo_path, check=True)
            logger.info("数据已从远程存储拉取")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"拉取数据失败: {e}")
            return False

    def create_data_pipeline(
        self,
        pipeline_name: str,
        stages: List[Dict[str, Any]],
        description: Optional[str] = None,
    ) -> bool:
        """
        创建数据处理管道

        Args:
            pipeline_name: 管道名称
            stages: 管道阶段
            description: 描述

        Returns:
            bool: 是否成功
        """
        if not self.dvc_initialized:
            logger.error("DVC未初始化，无法创建数据管道")
            return False

        try:
            # 创建管道配置文件
            pipeline_config = {
                "name": pipeline_name,
                "description": description,
                "stages": stages,
                "created_at": pd.Timestamp.now().isoformat(),
            }

            pipeline_file = self.repo_path / f"{pipeline_name}.dvc"
            with open(pipeline_file, "w", encoding="utf-8") as f:
                json.dump(pipeline_config, f, indent=2, ensure_ascii=False)

            # 跟踪管道文件
            subprocess.run(
                ["dvc", "add", str(pipeline_file)], cwd=self.repo_path, check=True
            )

            logger.info(f"数据管道已创建: {pipeline_name}")
            return True
        except Exception as e:
            logger.error(f"创建数据管道失败: {e}")
            return False

    def run_pipeline(self, pipeline_name: str) -> bool:
        """运行数据管道"""
        if not self.dvc_initialized:
            logger.error("DVC未初始化，无法运行数据管道")
            return False

        try:
            pipeline_file = self.repo_path / f"{pipeline_name}.dvc"
            if not pipeline_file.exists():
                logger.error(f"管道文件不存在: {pipeline_file}")
                return False

            # 运行管道
            subprocess.run(
                ["dvc", "repro", str(pipeline_file)], cwd=self.repo_path, check=True
            )

            logger.info(f"数据管道已运行: {pipeline_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"运行数据管道失败: {e}")
            return False

    def calculate_data_metrics(
        self, data_path: str, metrics_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        计算数据质量指标

        Args:
            data_path: 数据路径
            metrics_config: 指标配置

        Returns:
            Dict[str, Any]: 数据指标
        """
        try:
            data_path = Path(data_path)
            metrics = {}

            if data_path.is_file():
                # 单个文件
                if data_path.suffix == ".csv":
                    df = pd.read_csv(data_path)
                    metrics = self._calculate_dataframe_metrics(df, metrics_config)
                elif data_path.suffix in [".json", ".jsonl"]:
                    with open(data_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    metrics = self._calculate_json_metrics(data, metrics_config)
            elif data_path.is_dir():
                # 目录
                metrics = self._calculate_directory_metrics(data_path, metrics_config)

            # 添加文件信息
            metrics["file_path"] = str(data_path)
            metrics["file_size"] = self._get_file_size(data_path)
            metrics["file_hash"] = self._calculate_file_hash(data_path)
            metrics["calculated_at"] = pd.Timestamp.now().isoformat()

            # 存储指标
            self.data_metrics[str(data_path)] = metrics

            return metrics
        except Exception as e:
            logger.error(f"计算数据指标失败: {e}")
            return {}

    def _calculate_dataframe_metrics(
        self, df: pd.DataFrame, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """计算DataFrame指标"""
        metrics = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "memory_usage": df.memory_usage(deep=True).sum(),
            "null_count": df.isnull().sum().sum(),
            "duplicate_count": df.duplicated().sum(),
            "data_types": df.dtypes.to_dict(),
        }

        # 数值列统计
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            metrics["numeric_stats"] = df[numeric_cols].describe().to_dict()

        # 分类列统计
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns
        if len(categorical_cols) > 0:
            metrics["categorical_stats"] = {}
            for col in categorical_cols:
                metrics["categorical_stats"][col] = {
                    "unique_count": df[col].nunique(),
                    "most_common": df[col].mode().iloc[0]
                    if not df[col].mode().empty
                    else None,
                    "value_counts": df[col].value_counts().head(10).to_dict(),
                }

        return metrics

    def _calculate_json_metrics(
        self, data: Any, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """计算JSON数据指标"""
        metrics = {
            "data_type": type(data).__name__,
            "size_bytes": len(json.dumps(data).encode("utf-8")),
        }

        if isinstance(data, list):
            metrics["array_length"] = len(data)
            if data and isinstance(data[0], dict):
                metrics["object_keys"] = list(data[0].keys())
        elif isinstance(data, dict):
            metrics["object_keys"] = list(data.keys())
            metrics["object_size"] = len(data)

        return metrics

    def _calculate_directory_metrics(
        self, dir_path: Path, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """计算目录指标"""
        file_count = 0
        total_size = 0
        file_types = {}

        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                file_count += 1
                total_size += file_path.stat().st_size
                ext = file_path.suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1

        return {
            "file_count": file_count,
            "total_size": total_size,
            "file_types": file_types,
            "directory_depth": max(
                [
                    len(p.parts) - len(dir_path.parts)
                    for p in dir_path.rglob("*")
                    if p.is_file()
                ],
                default=0,
            ),
        }

    def _get_file_size(self, file_path: Path) -> int:
        """获取文件大小"""
        if file_path.is_file():
            return file_path.stat().st_size
        elif file_path.is_dir():
            return sum(f.stat().st_size for f in file_path.rglob("*") if f.is_file())
        return 0

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        hash_md5 = hashlib.md5()
        if file_path.is_file():
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def track_data_quality(
        self, data_path: str, quality_thresholds: Optional[Dict[str, float]] = None
    ) -> bool:
        """
        跟踪数据质量

        Args:
            data_path: 数据路径
            quality_thresholds: 质量阈值

        Returns:
            bool: 是否成功
        """
        try:
            # 计算数据指标
            metrics = self.calculate_data_metrics(data_path)

            # 检查质量阈值
            quality_issues = []
            if quality_thresholds:
                for metric, threshold in quality_thresholds.items():
                    if metric in metrics and metrics[metric] > threshold:
                        quality_issues.append(
                            f"{metric}: {metrics[metric]} > {threshold}"
                        )

            # 创建质量报告
            quality_report = {
                "data_path": data_path,
                "metrics": metrics,
                "quality_issues": quality_issues,
                "quality_score": self._calculate_quality_score(
                    metrics, quality_thresholds
                ),
                "checked_at": pd.Timestamp.now().isoformat(),
            }

            # 保存质量报告
            report_file = Path(data_path).with_suffix(".quality.json")
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(quality_report, f, indent=2, ensure_ascii=False, default=str)

            # 跟踪质量报告
            self.track_file(str(report_file))

            logger.info(f"数据质量已跟踪: {data_path}")
            return True
        except Exception as e:
            logger.error(f"跟踪数据质量失败: {e}")
            return False

    def _calculate_quality_score(
        self, metrics: Dict[str, Any], thresholds: Optional[Dict[str, float]] = None
    ) -> float:
        """计算数据质量评分"""
        score = 100.0

        if not thresholds:
            return score

        for metric, threshold in thresholds.items():
            if metric in metrics:
                if metrics[metric] > threshold:
                    # 超出阈值，扣分
                    penalty = min(20.0, (metrics[metric] - threshold) / threshold * 10)
                    score -= penalty

        return max(0.0, score)

    def get_data_lineage(self, file_path: str) -> Dict[str, Any]:
        """获取数据血缘"""
        try:
            # 查找相关的DVC文件
            dvc_file = Path(file_path + ".dvc")
            if not dvc_file.exists():
                return {"error": "未找到DVC文件"}

            # 读取DVC文件信息
            with open(dvc_file, "r", encoding="utf-8") as f:
                dvc_info = json.load(f)

            lineage = {
                "file_path": file_path,
                "dvc_info": dvc_info,
                "dependencies": dvc_info.get("deps", []),
                "outputs": dvc_info.get("outs", []),
                "metrics": dvc_info.get("metrics", []),
                "plots": dvc_info.get("plots", []),
            }

            return lineage
        except Exception as e:
            logger.error(f"获取数据血缘失败: {e}")
            return {"error": str(e)}

    def export_data_catalog(self, output_file: str) -> bool:
        """导出数据目录"""
        try:
            catalog = {
                "tracked_files": list(self.tracked_files),
                "data_metrics": self.data_metrics,
                "export_time": pd.Timestamp.now().isoformat(),
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(catalog, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"数据目录已导出: {output_file}")
            return True
        except Exception as e:
            logger.error(f"导出数据目录失败: {e}")
            return False
