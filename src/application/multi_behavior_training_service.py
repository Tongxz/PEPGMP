"""
多行为检测模型训练服务。
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import warnings
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.application.model_registry_service import (
    ModelRegistrationInfo,
    ModelRegistryService,
)
from src.config.multi_behavior_training_config import MultiBehaviorTrainingConfig

logger = logging.getLogger(__name__)


@dataclass
class MultiBehaviorTrainingResult:
    model_path: Path
    report_path: Path
    metrics: Dict[str, Any]
    samples_used: int
    version: str
    artifacts: Dict[str, Any]


class MultiBehaviorTrainingService:
    """调用 YOLOv8 进行多行为检测模型训练。"""

    def __init__(
        self,
        config: MultiBehaviorTrainingConfig,
        model_registry_service: Optional[ModelRegistryService] = None,
    ) -> None:
        self._config = config
        self._model_registry = model_registry_service

    async def train(
        self,
        dataset_dir: Path,
        data_config: Optional[Path] = None,
        training_params: Optional[Dict[str, Any]] = None,
        dataset_metadata: Optional[Dict[str, Any]] = None,
    ) -> MultiBehaviorTrainingResult:
        dataset_dir = Path(dataset_dir)
        data_config = (
            Path(data_config) if data_config is not None else dataset_dir / "data.yaml"
        )
        if not data_config.exists():
            raise FileNotFoundError(f"未找到 data.yaml: {data_config}")

        training_params = training_params or {}
        result = await asyncio.to_thread(
            self._run_training,
            dataset_dir,
            data_config,
            training_params,
        )

        if self._model_registry:
            try:
                dataset_info = dataset_metadata or {}
                registration = ModelRegistrationInfo(
                    name=training_params.get(
                        "model_name", f"multi_behavior_{result.version}"
                    ),
                    model_type=training_params.get("model_type", "multi_behavior"),
                    version=result.version,
                    model_path=result.model_path,
                    report_path=result.report_path,
                    dataset_id=dataset_info.get("dataset_id"),
                    dataset_path=dataset_info.get("dataset_path"),
                    metrics=result.metrics,
                    artifacts=result.artifacts,
                    training_params=training_params,
                    description=training_params.get("description"),
                )
                await self._model_registry.register_model(registration)
            except Exception as exc:  # pragma: no cover
                logger.warning("多行为模型注册失败: %s", exc)

        return result

    def _run_training(
        self,
        dataset_dir: Path,
        data_config: Path,
        training_params: Dict[str, Any],
    ) -> MultiBehaviorTrainingResult:
        try:
            from ultralytics import YOLO
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "未安装 ultralytics 库，无法执行多行为训练。请运行 `pip install ultralytics`。"
            ) from exc

        model_name = training_params.get("model", self._config.yolo_model)
        epochs = int(training_params.get("epochs", self._config.epochs))
        imgsz = int(training_params.get("image_size", self._config.image_size))
        batch_size = int(training_params.get("batch_size", self._config.batch_size))
        device_raw = training_params.get("device", self._config.device)
        # 智能选择设备：如果device="auto"，使用ModelConfig选择设备，否则使用指定设备
        device = self._select_device(device_raw)
        patience = int(training_params.get("patience", self._config.patience))
        run_name = training_params.get(
            "run_name", f"multi_behavior_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )

        # 学习率参数（从训练参数中获取，如果没有则使用合理的默认值）
        lr0 = float(training_params.get("lr0", 0.01))  # 初始学习率
        lrf = float(training_params.get("lrf", 0.1))  # 最终学习率（相对于lr0）
        momentum = float(training_params.get("momentum", 0.937))  # 动量
        weight_decay = float(training_params.get("weight_decay", 0.0005))  # 权重衰减
        warmup_epochs = float(training_params.get("warmup_epochs", 3.0))  # 预热轮数

        project_dir = self._config.output_dir / "runs"
        project_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "开始 YOLO 检测训练: model=%s epochs=%s imgsz=%s batch=%s device=%s lr0=%s lrf=%s",
            model_name,
            epochs,
            imgsz,
            batch_size,
            device,
            lr0,
            lrf,
        )

        model = YOLO(model_name)

        # 抑制 YOLO 的警告（这些警告通常不影响训练）
        # 特别是验证阶段指标计算的警告，这是YOLO的已知问题
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", category=RuntimeWarning, module="ultralytics"
            )
            warnings.filterwarnings("ignore", message=".*invalid value encountered.*")
            warnings.filterwarnings(
                "ignore", message=".*list.*argument.*must have no negative.*"
            )

            try:
                # 训练模型，即使验证阶段出现警告也继续
                # 注意：YOLO在训练过程中如果遇到验证阶段错误，可能会提前终止
                # 设置 save_period=1 确保每轮都保存模型（包括第1轮）
                # 重新启用数据增强以帮助模型学习，但使用更保守的设置
                model.train(
                    data=str(data_config),
                    epochs=epochs,
                    imgsz=imgsz,
                    batch=batch_size,
                    device=device,
                    patience=patience,
                    project=str(project_dir),
                    name=run_name,
                    exist_ok=True,
                    verbose=False,
                    save=True,  # 确保保存模型
                    save_period=1,  # 每轮都保存（包括第1轮）
                    rect=False,  # 禁用矩形训练（可能导致张量大小不匹配）
                    augment=True,  # 重新启用数据增强以帮助模型学习
                    val=True,  # 启用验证以获取验证集指标（mAP50, mAP50-95等）
                    # 优化器参数
                    lr0=lr0,  # 初始学习率
                    lrf=lrf,  # 最终学习率（相对于lr0）
                    momentum=momentum,  # 动量
                    weight_decay=weight_decay,  # 权重衰减
                    warmup_epochs=warmup_epochs,  # 预热轮数
                    # 数据增强参数（保守设置，避免张量大小问题）
                    hsv_h=0.015,  # 色调增强（降低）
                    hsv_s=0.7,  # 饱和度增强
                    hsv_v=0.4,  # 明度增强
                    degrees=0.0,  # 旋转角度（禁用旋转，避免张量问题）
                    translate=0.1,  # 平移
                    scale=0.5,  # 缩放
                    shear=0.0,  # 剪切（禁用，避免张量问题）
                    perspective=0.0,  # 透视变换（禁用，避免张量问题）
                    flipud=0.0,  # 上下翻转概率（禁用）
                    fliplr=0.5,  # 左右翻转概率
                    mosaic=0.5,  # Mosaic增强概率（降低，避免shape mismatch）
                    mixup=0.0,  # Mixup增强概率（禁用，避免张量问题）
                    copy_paste=0.0,  # Copy-paste增强（禁用，避免shape问题）
                )
            except (ValueError, RuntimeError, RuntimeWarning) as exc:
                # 捕获训练过程中的异常，提供更详细的错误信息
                error_msg = str(exc)
                error_lower = error_msg.lower()

                # 检查是否是验证阶段指标计算的问题
                # 这些错误通常发生在验证阶段计算指标时，但训练本身可能已经完成
                is_metrics_error = (
                    "negative" in error_lower
                    or "invalid value" in error_lower
                    or ("list" in error_lower and "negative" in error_lower)
                    or "argument must have no negative" in error_lower
                )

                # 检查是否是张量大小不匹配的错误
                is_tensor_size_error = (
                    "size of tensor" in error_lower and "must match" in error_lower
                ) or (
                    "shape mismatch" in error_lower or
                    "cannot be broadcast" in error_lower
                )

                if is_tensor_size_error:
                    logger.error(
                        "训练过程中出现张量形状不匹配错误，这通常是由于数据增强或数据集问题导致的。"
                        "错误: %s", exc
                    )
                    # 检查训练进度，如果已经训练了很多轮，可能是数据增强导致的问题
                    trainer = getattr(model, "trainer", None)
                    if trainer is not None:
                        current_epoch = getattr(trainer, "epoch", 0)
                        if current_epoch > 10:
                            # 已经训练了很多轮，可能是数据增强导致的问题
                            raise ValueError(
                                f"训练失败：张量形状不匹配（第{current_epoch}轮）。"
                                f"这通常是由于数据增强（特别是Mosaic）导致的问题。"
                                f"建议：1) 降低Mosaic增强概率；2) 禁用某些数据增强；"
                                f"3) 检查数据集中是否有异常的标注文件。原始错误: {error_msg}"
                            ) from exc
                    raise ValueError(
                        f"训练失败：张量形状不匹配。这通常是由于："
                        f"1) 数据增强（Mosaic等）导致标注索引问题；"
                        f"2) 标注文件与图像文件不匹配；"
                        f"3) 某些图像文件损坏或无法读取；"
                        f"4) 数据集中存在格式不一致的标注。"
                        f"建议：1) 降低Mosaic增强概率或禁用数据增强；"
                        f"2) 检查数据集完整性；3) 验证所有图像和标注文件是否匹配；"
                        f"4) 尝试重新下载或准备数据集。原始错误: {error_msg}"
                    ) from exc
                elif is_metrics_error:
                    logger.warning("训练过程中出现指标计算警告（通常在验证阶段），这是YOLO的已知问题。" "错误: %s", exc)

                    # 检查训练器是否存在，如果存在说明训练可能已经部分完成
                    trainer = getattr(model, "trainer", None)
                    if trainer is None:
                        # 如果训练器不存在，说明训练确实失败了
                        raise ValueError(
                            f"训练失败：验证阶段指标计算出现问题。这可能是由于某些类别在验证集中样本不足。"
                            f"建议：1) 增加验证集样本数量；2) 检查数据集中各类别是否平衡；"
                            f"3) 尝试减少验证集比例或使用更大的数据集。原始错误: {error_msg}"
                        ) from exc
                    else:
                        # 训练器存在，检查训练进度
                        current_epoch = getattr(trainer, "epoch", 0)
                        total_epochs = getattr(trainer, "epochs", epochs)
                        logger.info(
                            f"训练器存在，当前进度: {current_epoch}/{total_epochs} epochs。"
                            f"如果只完成了1轮，可能还没有保存模型文件。"
                        )

                        # 如果只完成了0轮，说明训练在验证阶段就失败了
                        if current_epoch == 0:
                            logger.error(
                                "训练在验证阶段就失败了（epoch=0），这通常是由于验证集指标计算问题。"
                                "验证已启用（val=True）以获取验证集指标，但如果验证阶段失败，训练会提前终止。"
                            )
                            # 抛出异常，因为训练没有真正开始
                            raise ValueError(
                                f"训练在验证阶段就失败了（epoch=0）。"
                                f"验证已启用（val=True）以获取验证集指标（mAP50, mAP50-95等），"
                                f"但验证阶段计算指标时出现问题。"
                                f"这可能是由于：1) 验证集中某些类别样本不足；2) 数据集格式问题；"
                                f"3) 图像文件损坏；4) 标注文件格式不正确。"
                                f"建议：1) 增加验证集样本数量；2) 检查数据集中各类别是否平衡；"
                                f"3) 检查数据集完整性；4) 验证所有图像和标注文件；"
                                f"5) 尝试使用更小的批次大小或调整其他训练参数。"
                            ) from exc
                        elif current_epoch <= 1:
                            logger.warning(
                                "训练只完成了 %d 轮，YOLO通常在第2轮之后才开始保存模型。"
                                "由于验证阶段错误，训练提前终止。"
                                "如果验证集指标计算出现问题，可以尝试："
                                "1) 增加验证集样本数量；2) 检查数据集中各类别是否平衡；"
                                "3) 尝试减少验证集比例或使用更大的数据集。",
                                current_epoch,
                            )
                            # 不抛出异常，继续尝试查找模型文件（可能在其他位置）
                        else:
                            logger.info("训练已完成多轮，继续处理模型文件...")
                else:
                    # 其他类型的错误
                    logger.error("训练失败: %s", exc)
                    raise
            except Exception as exc:
                # 其他异常直接抛出
                logger.error("训练过程中出现异常: %s", exc)
                raise

        trainer = getattr(model, "trainer", None)

        # 尝试多种方式找到保存目录和模型文件
        save_dir = None
        if trainer is not None:
            save_dir = Path(getattr(trainer, "save_dir", None))

        if save_dir is None or not save_dir.exists():
            # 尝试从项目目录查找
            save_dir = project_dir / run_name
            if not save_dir.exists():
                # 查找最新的运行目录
                run_dirs = sorted(
                    project_dir.glob(f"{run_name}*"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if run_dirs:
                    save_dir = run_dirs[0]
                    logger.info("使用找到的运行目录: %s", save_dir)
                else:
                    raise FileNotFoundError(f"未找到训练输出目录: {project_dir / run_name}")

        # 查找最佳模型文件
        best_model_path = None
        if trainer is not None:
            best_model_path = Path(getattr(trainer, "best", None))

        if best_model_path is None or not best_model_path.exists():
            # 尝试在保存目录中查找
            candidates = [
                save_dir / "weights" / "best.pt",
                save_dir / "best.pt",
                save_dir / "weights" / "last.pt",  # 如果没有best，使用last
                save_dir / "last.pt",
            ]
            for candidate in candidates:
                if candidate.exists():
                    best_model_path = candidate
                    logger.info(f"找到模型文件: {best_model_path}")
                    break

        if best_model_path is None or not best_model_path.exists():
            # 检查训练进度，如果只完成了1轮，这是正常的（YOLO通常从第2轮开始保存）
            trainer = getattr(model, "trainer", None)
            if trainer is not None:
                current_epoch = getattr(trainer, "epoch", 0)
                if current_epoch <= 1:
                    raise ValueError(
                        f"训练只完成了 {current_epoch} 轮，由于验证阶段错误提前终止。"
                        f"YOLO通常在第2轮之后才开始保存模型文件（即使设置了save_period=1）。"
                        f"建议：1) 增加训练轮数（epochs）；2) 检查数据集质量；"
                        f"3) 尝试使用更小的批次大小或调整其他训练参数；"
                        f"4) 考虑使用更小的验证集比例。"
                    )

            candidates_str = (
                [str(c) for c in candidates] if "candidates" in locals() else []
            )
            raise FileNotFoundError(f"未找到模型权重文件。检查了以下位置: {candidates_str}")

        metrics = self._extract_metrics(trainer, save_dir)

        self._config.output_dir.mkdir(parents=True, exist_ok=True)
        self._config.report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        model_path = self._config.output_dir / f"multi_behavior_{timestamp}.pt"
        report_path = (
            self._config.report_dir / f"multi_behavior_report_{timestamp}.json"
        )

        shutil.copy2(best_model_path, model_path)
        logger.info("多行为模型已保存: %s", model_path)

        # 尝试读取 annotations.json，如果不存在则使用数据集统计
        annotations_file = dataset_dir / "annotations.json"
        if annotations_file.exists():
            try:
                dataset_info = json.loads(annotations_file.read_text())
                samples_count = (
                    len(dataset_info) if isinstance(dataset_info, list) else 0
                )
            except Exception as exc:
                logger.warning("无法读取 annotations.json: %s，使用数据集统计", exc)
                # 统计训练集图像数量作为样本数
                train_images_dir = dataset_dir / "train" / "images"
                if train_images_dir.exists():
                    samples_count = len(list(train_images_dir.glob("*.jpg"))) + len(
                        list(train_images_dir.glob("*.png"))
                    )
                else:
                    samples_count = 0
        else:
            # 如果没有 annotations.json，统计训练集图像数量
            train_images_dir = dataset_dir / "train" / "images"
            if train_images_dir.exists():
                samples_count = len(list(train_images_dir.glob("*.jpg"))) + len(
                    list(train_images_dir.glob("*.png"))
                )
            else:
                samples_count = 0
            dataset_info = []  # 空列表，用于后续处理

        report_content = {
            "dataset_dir": str(dataset_dir),
            "data_config": str(data_config),
            "samples": samples_count,
            "training_params": {
                "model": model_name,
                "epochs": epochs,
                "image_size": imgsz,
                "batch_size": batch_size,
                "device": device,
                "patience": patience,
                **training_params,
            },
            "metrics": metrics,
            "generated_at": datetime.utcnow().isoformat(),
            "model_path": str(model_path),
        }

        report_path.write_text(json.dumps(report_content, indent=2, ensure_ascii=False))

        return MultiBehaviorTrainingResult(
            model_path=model_path,
            report_path=report_path,
            metrics=metrics,
            samples_used=samples_count,
            version=timestamp,
            artifacts={"yolo_run_directory": str(save_dir)},
        )

    def _select_device(self, device_request: str) -> str:
        """
        智能选择设备

        Args:
            device_request: 设备请求（'cpu'|'cuda'|'mps'|'auto'）

        Returns:
            最终设备字符串：'cpu'|'cuda'|'mps'
        """
        # 如果明确指定了设备，直接返回
        if device_request and device_request.lower() in {"cpu", "cuda", "mps"}:
            device_req = device_request.lower()
            # 验证设备是否可用
            try:
                import torch

                if device_req == "cuda" and not torch.cuda.is_available():
                    logger.warning("CUDA 不可用，回退到 CPU")
                    return "cpu"
                if device_req == "mps":
                    mps_available = bool(
                        getattr(torch.backends, "mps", None)
                        and torch.backends.mps.is_available()
                    )
                    if not mps_available:
                        logger.warning("MPS 不可用，回退到 CPU")
                        return "cpu"
                return device_req
            except ImportError:
                logger.warning("PyTorch 未安装，强制使用 CPU")
                return "cpu"

        # 如果device="auto"或未指定，使用ModelConfig选择设备
        try:
            from src.config.model_config import ModelConfig

            model_config = ModelConfig()
            device = model_config.select_device(requested=device_request)
            logger.info(f"设备选择: {device_request} -> {device}")
            return device
        except Exception as e:
            logger.warning(f"设备选择失败，使用 CPU: {e}")
            return "cpu"

    def _extract_metrics(self, trainer: Any, save_dir: Path) -> Dict[str, Any]:
        """提取训练指标，包括验证集指标（mAP50, mAP50-95等）"""
        metrics: Dict[str, Any] = {}
        
        # 从trainer对象提取指标
        if trainer is not None:
            trainer_metrics = getattr(trainer, "metrics", None)
            if isinstance(trainer_metrics, dict):
                for key, value in trainer_metrics.items():
                    try:
                        metrics[key] = self._to_serializable(value)
                    except Exception as exc:
                        logger.warning("提取指标 %s 失败: %s", key, exc)
                        # 跳过无法序列化的指标，继续处理其他指标
            
            # 尝试从trainer的results属性提取验证指标
            # YOLO的results对象通常包含验证指标，如metrics/mAP50, metrics/mAP50-95等
            try:
                results = getattr(trainer, "results", None)
                if results is not None:
                    # 尝试获取常见的验证指标
                    val_metrics = {}
                    for metric_name in ["metrics/mAP50", "metrics/mAP50-95", "metrics/precision", "metrics/recall"]:
                        try:
                            # 尝试从results对象获取指标
                            if hasattr(results, metric_name.replace("/", "_")):
                                value = getattr(results, metric_name.replace("/", "_"))
                                if value is not None:
                                    val_metrics[metric_name] = self._to_serializable(value)
                        except Exception:
                            pass
                    
                    # 如果找到了验证指标，添加到metrics中
                    if val_metrics:
                        metrics.setdefault("validation_metrics", val_metrics)
                        logger.info("提取到验证集指标: %s", list(val_metrics.keys()))
            except Exception as exc:
                logger.debug("从trainer.results提取验证指标失败: %s", exc)

        # 从results.json文件提取指标（这是YOLO保存指标的主要方式）
        results_json = save_dir / "results.json"
        if results_json.exists():
            try:
                results_data = json.loads(results_json.read_text())
                # 验证结果数据，过滤掉无效值
                if isinstance(results_data, dict):
                    cleaned_results = {}
                    for key, value in results_data.items():
                        try:
                            # 尝试转换为可序列化的值
                            cleaned_value = self._to_serializable(value)
                            # 检查是否为有效数值（不是 NaN 或 Inf）
                            if isinstance(cleaned_value, (int, float)):
                                import math

                                if not (
                                    math.isnan(cleaned_value)
                                    or math.isinf(cleaned_value)
                                ):
                                    cleaned_results[key] = cleaned_value
                            else:
                                cleaned_results[key] = cleaned_value
                        except Exception:
                            logger.debug("跳过无效的指标值: %s = %s", key, value)
                    
                    # 特别提取验证指标（通常以metrics/开头）
                    val_metrics_from_file = {}
                    for key, value in cleaned_results.items():
                        if key.startswith("metrics/") or "map" in key.lower():
                            val_metrics_from_file[key] = value
                    
                    if val_metrics_from_file:
                        metrics.setdefault("validation_metrics", val_metrics_from_file)
                        logger.info("从results.json提取到验证集指标: %s", list(val_metrics_from_file.keys()))
                    
                    # 合并到metrics中，优先使用trainer的指标
                    for key, value in cleaned_results.items():
                        if key not in metrics:
                            metrics[key] = value
                    metrics.setdefault("results", cleaned_results)
            except json.JSONDecodeError:
                logger.debug("无法解析 YOLO 结果文件: %s", results_json)
            except Exception as exc:
                logger.warning("处理 YOLO 结果文件时出错: %s", exc)
        
        return metrics

    @staticmethod
    def _to_serializable(value: Any) -> Any:
        import numpy as np

        if isinstance(value, (np.floating,)):
            return float(value)
        if isinstance(value, (np.integer,)):
            return int(value)
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:  # pragma: no cover
                return str(value)
        return value
