#!/usr/bin/env python
"""
发网检测诊断脚本

用于诊断发网检测模型为什么识别不到发网
"""

import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import cv2
import numpy as np
from ultralytics import YOLO

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_model_loading():
    """测试模型加载"""
    print("=" * 70)
    print("1. 测试模型加载")
    print("=" * 70)

    model_path = "models/hairnet_detection/hairnet_detection.pt"
    abs_path = project_root / model_path

    if not abs_path.exists():
        print(f"❌ 模型文件不存在: {abs_path}")
        return None

    print(f"✅ 模型文件存在: {abs_path}")
    print(f"   文件大小: {abs_path.stat().st_size / 1024 / 1024:.2f} MB")

    try:
        model = YOLO(str(abs_path))
        print(f"✅ 模型加载成功")
        print(f"   模型类别: {model.names}")
        print(f"   类别数量: {len(model.names)}")
        return model
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return None


def test_full_image_detection(model, image_path=None):
    """测试全图检测"""
    print("\n" + "=" * 70)
    print("2. 测试全图检测（不使用ROI）")
    print("=" * 70)

    if image_path is None:
        # 尝试从测试视频中提取一帧
        test_video = project_root / "tests/fixtures/videos/20250724072708.mp4"
        if test_video.exists():
            cap = cv2.VideoCapture(str(test_video))
            ret, frame = cap.read()
            cap.release()
            if ret:
                image_path = "temp_test_frame.jpg"
                cv2.imwrite(image_path, frame)
                print(f"✅ 从测试视频提取帧: {image_path}")
            else:
                print("❌ 无法从测试视频读取帧")
                return
        else:
            print("⚠️  未找到测试图像，跳过全图检测测试")
            return

    if not os.path.exists(image_path):
        print(f"❌ 图像文件不存在: {image_path}")
        return

    print(f"📷 测试图像: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ 无法读取图像: {image_path}")
        return

    print(f"   图像大小: {image.shape}")

    # 使用不同的阈值测试
    thresholds = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5]

    for conf_thres in thresholds:
        results = model(image, conf=conf_thres, iou=0.45, verbose=False)

        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    cls_name = model.names[cls]
                    detections.append(
                        {
                            "class": cls_name,
                            "confidence": conf,
                            "bbox": [x1, y1, x2, y2],
                        }
                    )

        hairnet_detections = [d for d in detections if d["class"].lower() == "hairnet"]
        head_detections = [d for d in detections if d["class"].lower() == "head"]
        person_detections = [d for d in detections if d["class"].lower() == "person"]

        print(f"\n   阈值 {conf_thres:.2f}:")
        print(f"     总检测数: {len(detections)}")
        print(f"     发网: {len(hairnet_detections)}")
        if hairnet_detections:
            for d in hairnet_detections:
                print(f"       - 置信度: {d['confidence']:.3f}, 位置: {d['bbox']}")
        print(f"     头部: {len(head_detections)}")
        print(f"     人体: {len(person_detections)}")

        if hairnet_detections:
            print(
                f"   ✅ 检测到发网！最低置信度: {min(d['confidence'] for d in hairnet_detections):.3f}"
            )


def test_roi_detection(model, image_path=None):
    """测试ROI检测（模拟实际检测流程）"""
    print("\n" + "=" * 70)
    print("3. 测试ROI检测（模拟实际检测流程）")
    print("=" * 70)

    if image_path is None:
        test_video = project_root / "tests/fixtures/videos/20250724072708.mp4"
        if test_video.exists():
            cap = cv2.VideoCapture(str(test_video))
            ret, frame = cap.read()
            cap.release()
            if ret:
                image_path = "temp_test_frame.jpg"
                cv2.imwrite(image_path, frame)
            else:
                print("❌ 无法从测试视频读取帧")
                return
        else:
            print("⚠️  未找到测试图像，跳过ROI检测测试")
            return

    if not os.path.exists(image_path):
        print(f"❌ 图像文件不存在: {image_path}")
        return

    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ 无法读取图像: {image_path}")
        return

    # 模拟人体检测结果（假设图像中有一个人）
    h, w = image.shape[:2]
    # 假设人体在图像中央，占图像高度的60%
    person_height = int(h * 0.6)
    person_width = int(w * 0.4)
    x1 = (w - person_width) // 2
    y1 = (h - person_height) // 2
    x2 = x1 + person_width
    y2 = y1 + person_height

    human_bbox = [x1, y1, x2, y2]
    print(f"📷 模拟人体检测框: {human_bbox}")

    # 提取头部ROI（与实际代码一致）
    person_height_actual = y2 - y1
    person_width_actual = x2 - x1
    head_height = int(person_height_actual * 0.35)  # 35%
    padding_height = int(head_height * 0.2)  # 20%
    padding_width = int(person_width_actual * 0.1)  # 10%

    roi_x1 = max(0, x1 - padding_width)
    roi_y1 = max(0, y1 - padding_height)
    roi_x2 = min(w, x2 + padding_width)
    roi_y2 = min(h, y1 + head_height + padding_height)

    head_roi = image[roi_y1:roi_y2, roi_x1:roi_x2]

    print(f"   头部ROI: ({roi_x1}, {roi_y1}) -> ({roi_x2}, {roi_y2})")
    print(f"   ROI大小: {head_roi.shape}")

    if head_roi.size == 0:
        print("❌ ROI为空")
        return

    # 保存ROI图像用于检查
    roi_path = "temp_head_roi.jpg"
    cv2.imwrite(roi_path, head_roi)
    print(f"   ✅ ROI图像已保存: {roi_path}")

    # 图像预处理（与实际代码一致）
    try:
        lab = cv2.cvtColor(head_roi, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        head_roi_processed = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

        # 锐化
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]]) * 0.1
        head_roi_processed = cv2.filter2D(head_roi_processed, -1, kernel)

        processed_path = "temp_head_roi_processed.jpg"
        cv2.imwrite(processed_path, head_roi_processed)
        print(f"   ✅ 预处理后ROI图像已保存: {processed_path}")
    except Exception as e:
        print(f"   ⚠️  预处理失败: {e}，使用原始ROI")
        head_roi_processed = head_roi

    # 使用不同的阈值测试ROI检测
    thresholds = [0.1, 0.15, 0.2, 0.25, 0.3]

    print(f"\n   使用不同阈值测试ROI检测:")
    for conf_thres in thresholds:
        results = model(head_roi_processed, conf=conf_thres, iou=0.45, verbose=False)

        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    cls_name = model.names[cls]
                    detections.append({"class": cls_name, "confidence": conf})

        hairnet_detections = [d for d in detections if d["class"].lower() == "hairnet"]

        print(f"     阈值 {conf_thres:.2f}: 检测到 {len(detections)} 个目标")
        if hairnet_detections:
            print(f"       ✅ 发网: {len(hairnet_detections)} 个")
            for d in hairnet_detections:
                print(f"          - 置信度: {d['confidence']:.3f}")
        else:
            if detections:
                classes = [d["class"] for d in detections]
                print(f"       ⚠️  检测到其他类别: {set(classes)}")
            else:
                print(f"       ❌ 未检测到任何目标")


def check_configuration():
    """检查配置"""
    print("\n" + "=" * 70)
    print("4. 检查配置")
    print("=" * 70)

    try:
        from src.config.unified_params import get_unified_params

        params = get_unified_params()
        hairnet_params = params.hairnet_detection

        print(f"✅ 配置加载成功")
        print(f"   模型路径: {hairnet_params.model_path}")
        print(f"   置信度阈值: {hairnet_params.confidence_threshold}")
        print(f"   设备: {hairnet_params.device}")
        print(f"   总分阈值: {hairnet_params.total_score_threshold}")

        # 检查模型文件是否存在
        model_path = project_root / hairnet_params.model_path
        if model_path.exists():
            print(f"   ✅ 模型文件存在: {model_path}")
        else:
            print(f"   ❌ 模型文件不存在: {model_path}")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("发网检测诊断工具")
    print("=" * 70)

    # 1. 测试模型加载
    model = test_model_loading()
    if model is None:
        print("\n❌ 模型加载失败，无法继续诊断")
        return

    # 2. 检查配置
    check_configuration()

    # 3. 测试全图检测
    test_full_image_detection(model)

    # 4. 测试ROI检测
    test_roi_detection(model)

    print("\n" + "=" * 70)
    print("诊断完成")
    print("=" * 70)
    print("\n建议:")
    print("1. 查看生成的临时图像文件（temp_*.jpg）检查ROI是否正确")
    print("2. 如果全图检测能检测到发网，但ROI检测不能，说明ROI提取有问题")
    print("3. 如果全图检测也检测不到，说明模型或阈值有问题")
    print("4. 检查日志中的实际检测结果")


if __name__ == "__main__":
    main()
