"""
数据集验证服务
提供数据集文件完整性校验和结构验证功能
"""

import io
import logging
import tarfile
import zipfile
from pathlib import Path
from typing import List, Tuple

from fastapi import UploadFile

logger = logging.getLogger(__name__)


class DatasetValidationService:
    """数据集验证服务"""

    @staticmethod
    async def validate_file(
        file: UploadFile, validate_content: bool = True
    ) -> Tuple[bool, str]:
        """
        验证单个文件

        Args:
            file: 上传的文件
            validate_content: 是否验证文件内容（完整性检查）

        Returns:
            (is_valid, error_message)
        """
        filename = file.filename.lower() if file.filename else ""

        # 1. 检查文件扩展名
        if not filename:
            return False, "文件名不能为空"

        # 2. ZIP 文件校验
        if filename.endswith(".zip"):
            return await DatasetValidationService._validate_zip_file(
                file, validate_content
            )

        # 3. TAR 文件校验
        elif filename.endswith((".tar", ".tar.gz", ".tgz")):
            return await DatasetValidationService._validate_tar_file(
                file, validate_content
            )

        # 4. YAML 文件校验（data.yaml）
        elif filename.endswith((".yaml", ".yml")):
            return await DatasetValidationService._validate_yaml_file(file)

        # 5. 图像文件校验（可选）
        elif filename.endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
            # 基础校验：只检查文件大小
            try:
                content = await file.read()
                await file.seek(0)  # 重置文件指针
                if len(content) == 0:
                    return False, "图像文件为空"
                if len(content) < 100:  # 最小文件大小检查
                    return False, "图像文件过小，可能已损坏"
                return True, ""
            except Exception as e:
                return False, f"图像文件读取失败: {str(e)}"

        # 6. 文本文件（标注文件）
        elif filename.endswith(".txt"):
            return await DatasetValidationService._validate_text_file(file)

        # 7. 其他文件类型（默认通过，但记录警告）
        else:
            logger.warning(f"未知文件类型: {filename}，跳过校验")
            return True, ""

    @staticmethod
    async def _validate_zip_file(
        file: UploadFile, validate_content: bool
    ) -> Tuple[bool, str]:
        """验证 ZIP 文件"""
        try:
            # 读取文件内容到内存
            content = await file.read()
            await file.seek(0)  # 重置文件指针

            if len(content) == 0:
                return False, "ZIP 文件为空"

            # 尝试打开 ZIP 文件
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
                    # 检查 ZIP 文件是否损坏
                    if validate_content:
                        bad_file = zip_file.testzip()
                        if bad_file:
                            return False, f"ZIP 文件损坏: {bad_file}"

                    # 检查是否包含必要文件（可选）
                    file_list = zip_file.namelist()
                    if len(file_list) == 0:
                        return False, "ZIP 文件为空（不包含任何文件）"

                    # 检查是否有 data.yaml（如果是数据集压缩包）
                    has_yaml = any(
                        "data.yaml" in f.lower() or "data.yml" in f.lower()
                        for f in file_list
                    )
                    if not has_yaml:
                        logger.warning("ZIP 文件中未找到 data.yaml，可能不是标准数据集格式")

                    return True, ""
            except zipfile.BadZipFile:
                return False, "不是有效的 ZIP 文件格式"
            except zipfile.LargeZipFile:
                return False, "ZIP 文件过大（超过 4GB），请使用其他格式"
        except Exception as e:
            logger.error(f"ZIP 文件校验异常: {e}")
            return False, f"ZIP 文件校验失败: {str(e)}"

    @staticmethod
    async def _validate_tar_file(
        file: UploadFile, validate_content: bool
    ) -> Tuple[bool, str]:
        """验证 TAR 文件"""
        try:
            # 读取文件内容到内存
            content = await file.read()
            await file.seek(0)  # 重置文件指针

            if len(content) == 0:
                return False, "TAR 文件为空"

            # 确定 TAR 模式
            filename = file.filename.lower() if file.filename else ""
            mode = "r:gz" if filename.endswith((".tar.gz", ".tgz")) else "r"

            # 尝试打开 TAR 文件
            try:
                with tarfile.open(fileobj=io.BytesIO(content), mode=mode) as tar_file:
                    # 检查 TAR 文件是否损坏
                    if validate_content:
                        try:
                            tar_file.getmembers()  # 尝试读取成员列表
                        except tarfile.TarError as e:
                            return False, f"TAR 文件损坏: {str(e)}"

                    # 检查文件列表
                    file_list = tar_file.getnames()
                    if len(file_list) == 0:
                        return False, "TAR 文件为空（不包含任何文件）"

                    # 检查是否有 data.yaml
                    has_yaml = any(
                        "data.yaml" in f.lower() or "data.yml" in f.lower()
                        for f in file_list
                    )
                    if not has_yaml:
                        logger.warning("TAR 文件中未找到 data.yaml，可能不是标准数据集格式")

                    return True, ""
            except tarfile.TarError as e:
                return False, f"TAR 文件格式错误: {str(e)}"
        except Exception as e:
            logger.error(f"TAR 文件校验异常: {e}")
            return False, f"TAR 文件校验失败: {str(e)}"

    @staticmethod
    async def _validate_yaml_file(file: UploadFile) -> Tuple[bool, str]:
        """验证 YAML 文件"""
        try:
            content = await file.read()
            await file.seek(0)

            if len(content) == 0:
                return False, "YAML 文件为空"

            # 尝试解析 YAML（基础检查）
            try:
                import yaml

                yaml.safe_load(content.decode("utf-8"))
                return True, ""
            except yaml.YAMLError as e:
                return False, f"YAML 文件格式错误: {str(e)}"
            except UnicodeDecodeError:
                return False, "YAML 文件编码错误（应为 UTF-8）"
        except Exception as e:
            logger.error(f"YAML 文件校验异常: {e}")
            return False, f"YAML 文件校验失败: {str(e)}"

    @staticmethod
    async def _validate_text_file(file: UploadFile) -> Tuple[bool, str]:
        """验证文本文件（标注文件）"""
        try:
            content = await file.read()
            await file.seek(0)

            if len(content) == 0:
                return False, "文本文件为空"

            # 基础检查：尝试解码
            try:
                content.decode("utf-8")
                return True, ""
            except UnicodeDecodeError:
                return False, "文本文件编码错误（应为 UTF-8）"
        except Exception as e:
            logger.error(f"文本文件校验异常: {e}")
            return False, f"文本文件校验失败: {str(e)}"

    @staticmethod
    async def validate_files(
        files: List[UploadFile], validate_content: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        批量验证文件

        Args:
            files: 文件列表
            validate_content: 是否验证文件内容

        Returns:
            (all_valid, error_messages)
        """
        errors = []
        all_valid = True

        for file in files:
            is_valid, error_msg = await DatasetValidationService.validate_file(
                file, validate_content
            )
            if not is_valid:
                all_valid = False
                error_msg_full = f"{file.filename}: {error_msg}"
                errors.append(error_msg_full)
                logger.warning(f"文件校验失败: {error_msg_full}")

        return all_valid, errors

    @staticmethod
    async def validate_dataset_structure(
        dataset_dir: Path, require_yolo_format: bool = False
    ) -> Tuple[bool, str]:
        """
        验证数据集目录结构

        Args:
            dataset_dir: 数据集目录路径
            require_yolo_format: 是否要求 YOLO 格式

        Returns:
            (is_valid, error_message)
        """
        if not dataset_dir.exists():
            return False, f"数据集目录不存在: {dataset_dir}"

        if require_yolo_format:
            return await DatasetValidationService._validate_yolo_structure(dataset_dir)

        # 基础检查：至少有一些文件
        files = list(dataset_dir.rglob("*"))
        if len(files) == 0:
            return False, "数据集目录为空"

        return True, ""

    @staticmethod
    async def _validate_yolo_structure(dataset_dir: Path) -> Tuple[bool, str]:
        """验证 YOLO 数据集结构"""
        try:
            import yaml

            # 1. 检查 data.yaml 文件
            yaml_path = dataset_dir / "data.yaml"
            if not yaml_path.exists():
                # 尝试在子目录中查找
                yaml_files = list(dataset_dir.rglob("data.yaml"))
                if yaml_files:
                    yaml_path = yaml_files[0]
                else:
                    return False, "缺少 data.yaml 配置文件"

            # 2. 解析 data.yaml
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data_config = yaml.safe_load(f)
            except Exception as e:
                return False, f"data.yaml 解析失败: {str(e)}"

            if not data_config:
                return False, "data.yaml 文件为空"

            # 3. 检查必要字段
            required_fields = ["train", "val", "nc", "names"]
            missing_fields = [f for f in required_fields if f not in data_config]
            if missing_fields:
                return False, f"data.yaml 缺少必要字段: {', '.join(missing_fields)}"

            # 4. 检查目录结构（相对路径）
            base_path = yaml_path.parent
            train_path = base_path / data_config.get("train", "")
            val_path = base_path / data_config.get("val", "")

            # 如果路径是绝对路径，直接使用
            if Path(data_config.get("train", "")).is_absolute():
                train_path = Path(data_config.get("train", ""))
            if Path(data_config.get("val", "")).is_absolute():
                val_path = Path(data_config.get("val", ""))

            if not train_path.exists():
                return False, f"训练集目录不存在: {train_path}"

            if not val_path.exists():
                return False, f"验证集目录不存在: {val_path}"

            # 5. 检查图像和标注文件（可选，不强制）
            train_images = list(train_path.rglob("*.jpg")) + list(
                train_path.rglob("*.png")
            )
            train_labels = list(train_path.rglob("*.txt"))

            if len(train_images) == 0:
                logger.warning("训练集没有图像文件")
            if len(train_labels) == 0:
                logger.warning("训练集没有标注文件")

            return True, ""
        except Exception as e:
            logger.error(f"YOLO 结构验证异常: {e}")
            return False, f"数据集结构验证失败: {str(e)}"
