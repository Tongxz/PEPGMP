"""
测试数据集验证功能
"""
import asyncio
import io
import logging
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import UploadFile

from src.application.dataset_validation_service import DatasetValidationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_zip_file(valid: bool = True) -> bytes:
    """创建测试 ZIP 文件"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        if valid:
            zip_file.writestr(
                "data.yaml", "train: train/images\nval: valid/images\nnc: 2"
            )
            zip_file.writestr("train/images/img1.jpg", b"fake image data")
            zip_file.writestr("train/labels/img1.txt", "0 0.5 0.5 0.1 0.1")
        else:
            # 创建损坏的 ZIP 文件（不关闭，导致文件不完整）
            zip_file.writestr("test.txt", "test content")
            # 不调用 close()，导致文件损坏
    buffer.seek(0)
    return buffer.read()


def create_test_tar_file(valid: bool = True) -> bytes:
    """创建测试 TAR 文件"""
    import tarfile

    buffer = io.BytesIO()
    mode = "w:gz"
    with tarfile.open(fileobj=buffer, mode=mode) as tar_file:
        if valid:
            info = tarfile.TarInfo(name="data.yaml")
            info.size = len(b"train: train/images\nval: valid/images\nnc: 2")
            tar_file.addfile(
                info, io.BytesIO(b"train: train/images\nval: valid/images\nnc: 2")
            )
        else:
            # 创建损坏的 TAR 文件
            info = tarfile.TarInfo(name="test.txt")
            info.size = len(b"test content")
            tar_file.addfile(info, io.BytesIO(b"test content"))
            # 不关闭，导致文件损坏
    buffer.seek(0)
    return buffer.read()


async def test_zip_validation():
    """测试 ZIP 文件验证"""
    logger.info("=" * 60)
    logger.info("测试: ZIP 文件验证")
    logger.info("=" * 60)

    # 测试1: 有效的 ZIP 文件
    logger.info("测试1: 有效的 ZIP 文件")
    valid_zip_data = create_test_zip_file(valid=True)
    file1 = UploadFile(
        filename="test_dataset.zip",
        file=io.BytesIO(valid_zip_data),
    )
    is_valid, error = await DatasetValidationService.validate_file(file1)
    logger.info(f"  结果: {'✅ 通过' if is_valid else '❌ 失败'}")
    if not is_valid:
        logger.error(f"  错误: {error}")
    assert is_valid, f"有效 ZIP 文件应该通过验证: {error}"

    # 测试2: 损坏的 ZIP 文件
    logger.info("测试2: 损坏的 ZIP 文件")
    # 创建一个明显损坏的 ZIP 文件
    invalid_zip_data = b"This is not a valid ZIP file"
    file2 = UploadFile(
        filename="invalid.zip",
        file=io.BytesIO(invalid_zip_data),
    )
    is_valid, error = await DatasetValidationService.validate_file(file2)
    logger.info(f"  结果: {'✅ 正确拒绝' if not is_valid else '❌ 应该拒绝'}")
    if is_valid:
        logger.error(f"  错误: 损坏的 ZIP 文件应该被拒绝")
    assert not is_valid, "损坏的 ZIP 文件应该被拒绝"

    # 测试3: 空的 ZIP 文件
    logger.info("测试3: 空的 ZIP 文件")
    empty_zip_data = b""
    file3 = UploadFile(
        filename="empty.zip",
        file=io.BytesIO(empty_zip_data),
    )
    is_valid, error = await DatasetValidationService.validate_file(file3)
    logger.info(f"  结果: {'✅ 正确拒绝' if not is_valid else '❌ 应该拒绝'}")
    assert not is_valid, "空的 ZIP 文件应该被拒绝"

    logger.info("✅ ZIP 文件验证测试通过\n")


async def test_tar_validation():
    """测试 TAR 文件验证"""
    logger.info("=" * 60)
    logger.info("测试: TAR 文件验证")
    logger.info("=" * 60)

    # 测试1: 有效的 TAR 文件
    logger.info("测试1: 有效的 TAR.GZ 文件")
    valid_tar_data = create_test_tar_file(valid=True)
    file1 = UploadFile(
        filename="test_dataset.tar.gz",
        file=io.BytesIO(valid_tar_data),
    )
    is_valid, error = await DatasetValidationService.validate_file(file1)
    logger.info(f"  结果: {'✅ 通过' if is_valid else '❌ 失败'}")
    if not is_valid:
        logger.error(f"  错误: {error}")
    assert is_valid, f"有效 TAR 文件应该通过验证: {error}"

    # 测试2: 损坏的 TAR 文件
    logger.info("测试2: 损坏的 TAR 文件")
    invalid_tar_data = b"This is not a valid TAR file"
    file2 = UploadFile(
        filename="invalid.tar.gz",
        file=io.BytesIO(invalid_tar_data),
    )
    is_valid, error = await DatasetValidationService.validate_file(file2)
    logger.info(f"  结果: {'✅ 正确拒绝' if not is_valid else '❌ 应该拒绝'}")
    assert not is_valid, "损坏的 TAR 文件应该被拒绝"

    logger.info("✅ TAR 文件验证测试通过\n")


async def test_image_validation():
    """测试图像文件验证"""
    logger.info("=" * 60)
    logger.info("测试: 图像文件验证")
    logger.info("=" * 60)

    # 测试1: 有效的图像文件（模拟）
    logger.info("测试1: 有效的图像文件")
    valid_image_data = b"\xff\xd8\xff\xe0" + b"x" * 100  # 模拟 JPEG 文件头
    file1 = UploadFile(
        filename="test.jpg",
        file=io.BytesIO(valid_image_data),
    )
    is_valid, error = await DatasetValidationService.validate_file(file1)
    logger.info(f"  结果: {'✅ 通过' if is_valid else '❌ 失败'}")
    assert is_valid, f"有效图像文件应该通过验证: {error}"

    # 测试2: 空的图像文件
    logger.info("测试2: 空的图像文件")
    empty_image_data = b""
    file2 = UploadFile(
        filename="empty.jpg",
        file=io.BytesIO(empty_image_data),
    )
    is_valid, error = await DatasetValidationService.validate_file(file2)
    logger.info(f"  结果: {'✅ 正确拒绝' if not is_valid else '❌ 应该拒绝'}")
    assert not is_valid, "空的图像文件应该被拒绝"

    logger.info("✅ 图像文件验证测试通过\n")


async def test_batch_validation():
    """测试批量文件验证"""
    logger.info("=" * 60)
    logger.info("测试: 批量文件验证")
    logger.info("=" * 60)

    files = [
        UploadFile(
            filename="valid.zip",
            file=io.BytesIO(create_test_zip_file(valid=True)),
        ),
        UploadFile(
            filename="test.jpg",
            file=io.BytesIO(b"\xff\xd8\xff\xe0" + b"x" * 100),
        ),
        UploadFile(
            filename="invalid.zip",
            file=io.BytesIO(b"not a zip file"),
        ),
    ]

    all_valid, errors = await DatasetValidationService.validate_files(files)
    logger.info(f"结果: {'❌ 部分文件验证失败（预期）' if not all_valid else '✅ 所有文件通过'}")
    logger.info(f"错误数量: {len(errors)}")
    for error in errors:
        logger.info(f"  - {error}")

    assert not all_valid, "应该检测到无效文件"
    assert len(errors) > 0, "应该有错误信息"

    logger.info("✅ 批量文件验证测试通过\n")


async def main():
    """运行所有测试"""
    logger.info("开始测试数据集验证功能...\n")

    try:
        await test_zip_validation()
        await test_tar_validation()
        await test_image_validation()
        await test_batch_validation()

        logger.info("=" * 60)
        logger.info("✅ 所有测试通过")
        logger.info("=" * 60)
    except AssertionError as e:
        logger.error(f"❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
