#!/usr/bin/env python
"""
发网检测ROI诊断脚本 - 使用实际人体检测结果
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import cv2
import numpy as np
from ultralytics import YOLO

# 加载模型
model_path = project_root / "models/hairnet_detection/hairnet_detection.pt"
hairnet_model = YOLO(str(model_path))

# 加载人体检测模型
human_model_path = project_root / "models/yolo/yolov8s.pt"
human_model = YOLO(str(human_model_path))

# 读取测试图像
test_video = project_root / "tests/fixtures/videos/20250724072708.mp4"
cap = cv2.VideoCapture(str(test_video))
ret, frame = cap.read()
cap.release()

if not ret:
    print("无法读取测试视频")
    sys.exit(1)

print("=" * 70)
print("发网检测ROI诊断 - 使用实际人体检测结果")
print("=" * 70)

# 1. 人体检测
print("\n1. 进行人体检测...")
human_results = human_model(frame, conf=0.5, iou=0.6, verbose=False)

person_detections = []
for r in human_results:
    boxes = r.boxes
    if boxes is not None:
        for box in boxes:
            cls = int(box.cls[0])
            if human_model.names[cls] == "person":
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                person_detections.append(
                    {
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                        "confidence": conf,
                    }
                )

print(f"   检测到 {len(person_detections)} 个人")

if len(person_detections) == 0:
    print("❌ 未检测到人体，无法继续")
    sys.exit(1)

# 2. 全图发网检测（作为参考）
print("\n2. 全图发网检测（作为参考）...")
hairnet_full_results = hairnet_model(
    frame, conf=0.15, iou=0.45, imgsz=640, verbose=False
)

full_hairnet_detections = []
for r in hairnet_full_results:
    boxes = r.boxes
    if boxes is not None:
        for box in boxes:
            cls = int(box.cls[0])
            if hairnet_model.names[cls] == "hairnet":
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                full_hairnet_detections.append(
                    {
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                        "confidence": conf,
                    }
                )

print(f"   全图检测到 {len(full_hairnet_detections)} 个发网")
for i, det in enumerate(full_hairnet_detections):
    print(f"     发网 {i+1}: 置信度={det['confidence']:.3f}, 位置={det['bbox']}")

# 3. 对每个人进行ROI检测
print("\n3. ROI检测（使用实际人体检测框）...")
h, w = frame.shape[:2]

for i, person in enumerate(person_detections):
    print(f"\n   人员 {i+1}:")
    human_bbox = person["bbox"]
    x1, y1, x2, y2 = map(int, human_bbox)
    print(f"     人体框: ({x1}, {y1}) -> ({x2}, {y2})")
    print(f"     人体大小: {x2-x1} x {y2-y1}")

    # 提取头部ROI（与实际代码一致）
    person_height = y2 - y1
    person_width = x2 - x1
    head_height = int(person_height * 0.35)
    padding_height = int(head_height * 0.2)
    padding_width = int(person_width * 0.1)

    roi_x1 = max(0, x1 - padding_width)
    roi_y1 = max(0, y1 - padding_height)
    roi_x2 = min(w, x2 + padding_width)
    roi_y2 = min(h, y1 + head_height + padding_height)

    head_roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]

    print(f"     头部ROI: ({roi_x1}, {roi_y1}) -> ({roi_x2}, {roi_y2})")
    print(f"     ROI大小: {roi_x2-roi_x1} x {roi_y2-roi_y1}")

    if head_roi.size == 0:
        print(f"     ❌ ROI为空")
        continue

    # 保存ROI图像
    roi_path = f"temp_roi_person_{i+1}.jpg"
    cv2.imwrite(roi_path, head_roi)
    print(f"     ✅ ROI图像已保存: {roi_path}")

    # 图像预处理
    try:
        lab = cv2.cvtColor(head_roi, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        head_roi_processed = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]]) * 0.1
        head_roi_processed = cv2.filter2D(head_roi_processed, -1, kernel)

        processed_path = f"temp_roi_processed_person_{i+1}.jpg"
        cv2.imwrite(processed_path, head_roi_processed)
    except Exception as e:
        print(f"     ⚠️  预处理失败: {e}")
        head_roi_processed = head_roi

    # 在ROI上检测发网（指定imgsz=640与训练时保持一致）
    roi_results = hairnet_model(
        head_roi_processed, conf=0.15, iou=0.45, imgsz=640, verbose=False
    )

    roi_detections = []
    for r in roi_results:
        boxes = r.boxes
        if boxes is not None:
            for box in boxes:
                cls = int(box.cls[0])
                cls_name = hairnet_model.names[cls]
                conf = float(box.conf[0])
                roi_detections.append({"class": cls_name, "confidence": conf})

    hairnet_in_roi = [d for d in roi_detections if d["class"] == "hairnet"]

    print(f"     ROI检测结果:")
    print(f"       总检测数: {len(roi_detections)}")
    if hairnet_in_roi:
        print(f"       ✅ 检测到发网: {len(hairnet_in_roi)} 个")
        for d in hairnet_in_roi:
            print(f"          - 置信度: {d['confidence']:.3f}")
    else:
        if roi_detections:
            classes = set(d["class"] for d in roi_detections)
            print(f"       ⚠️  检测到其他类别: {classes}")
        else:
            print(f"       ❌ 未检测到任何目标")

    # 检查全图检测的发网是否在ROI内
    print(f"     全图发网与ROI的关系:")
    for j, full_hairnet in enumerate(full_hairnet_detections):
        hx1, hy1, hx2, hy2 = full_hairnet["bbox"]
        hx_center = (hx1 + hx2) / 2
        hy_center = (hy1 + hy2) / 2

        in_roi = roi_x1 <= hx_center <= roi_x2 and roi_y1 <= hy_center <= roi_y2
        print(
            f"       发网 {j+1} (置信度={full_hairnet['confidence']:.3f}): "
            f"中心=({hx_center:.0f}, {hy_center:.0f}), "
            f"在ROI内={'✅' if in_roi else '❌'}"
        )

# 4. 可视化
print("\n4. 创建可视化图像...")
vis_frame = frame.copy()

# 绘制人体检测框
for person in person_detections:
    x1, y1, x2, y2 = map(int, person["bbox"])
    cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(
        vis_frame,
        "Person",
        (x1, y1 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 0),
        2,
    )

# 绘制全图发网检测框
for hairnet in full_hairnet_detections:
    x1, y1, x2, y2 = map(int, hairnet["bbox"])
    cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
    cv2.putText(
        vis_frame,
        f"Hairnet {hairnet['confidence']:.2f}",
        (x1, y1 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 0, 0),
        2,
    )

# 绘制ROI区域
for i, person in enumerate(person_detections):
    x1, y1, x2, y2 = map(int, person["bbox"])
    person_height = y2 - y1
    person_width = x2 - x1
    head_height = int(person_height * 0.35)
    padding_height = int(head_height * 0.2)
    padding_width = int(person_width * 0.1)

    roi_x1 = max(0, x1 - padding_width)
    roi_y1 = max(0, y1 - padding_height)
    roi_x2 = min(w, x2 + padding_width)
    roi_y2 = min(h, y1 + head_height + padding_height)

    cv2.rectangle(vis_frame, (roi_x1, roi_y1), (roi_x2, roi_y2), (0, 255, 255), 2)
    cv2.putText(
        vis_frame,
        f"ROI {i+1}",
        (roi_x1, roi_y1 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 255),
        2,
    )

cv2.imwrite("temp_visualization.jpg", vis_frame)
print("   ✅ 可视化图像已保存: temp_visualization.jpg")

print("\n" + "=" * 70)
print("诊断完成")
print("=" * 70)
print("\n分析:")
print("1. 如果全图检测能检测到发网，但ROI检测不能，说明ROI位置不准确")
print("2. 检查可视化图像，确认ROI是否包含发网区域")
print("3. 如果ROI不包含发网，需要调整ROI提取逻辑")
