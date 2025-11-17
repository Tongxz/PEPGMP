#!/usr/bin/env python
"""测试不使用预处理的ROI检测"""

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import cv2
from ultralytics import YOLO

# 加载模型
hairnet_model = YOLO(str(project_root / "models/hairnet_detection/hairnet_detection.pt"))
human_model = YOLO(str(project_root / "models/yolo/yolov8s.pt"))

# 读取测试图像
test_video = project_root / "tests/fixtures/videos/20250724072708.mp4"
cap = cv2.VideoCapture(str(test_video))
ret, frame = cap.read()
cap.release()

# 人体检测
human_results = human_model(frame, conf=0.5, iou=0.6, verbose=False)
person_detections = []
for r in human_results:
    boxes = r.boxes
    if boxes is not None:
        for box in boxes:
            cls = int(box.cls[0])
            if human_model.names[cls] == "person":
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                person_detections.append({
                    "bbox": [float(x1), float(y1), float(x2), float(y2)]
                })

print("=" * 70)
print("测试ROI检测（不使用预处理）")
print("=" * 70)

h, w = frame.shape[:2]

for i, person in enumerate(person_detections[:2]):  # 只测试前2个人
    print(f"\n人员 {i+1}:")
    x1, y1, x2, y2 = map(int, person["bbox"])
    
    # 提取ROI（与实际代码一致）
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
    
    print(f"  ROI大小: {head_roi.shape}")
    
    # 测试1: 原始ROI（不使用预处理）
    print(f"  测试1: 原始ROI（不使用预处理）")
    results1 = hairnet_model(head_roi, conf=0.15, iou=0.45, imgsz=640, verbose=False)
    detections1 = []
    for r in results1:
        boxes = r.boxes
        if boxes is not None:
            for box in boxes:
                cls = int(box.cls[0])
                if hairnet_model.names[cls] == "hairnet":
                    conf = float(box.conf[0])
                    detections1.append(conf)
    print(f"    结果: {'✅ 检测到发网' if detections1 else '❌ 未检测到'}")
    if detections1:
        print(f"    置信度: {detections1}")
    
    # 测试2: 使用预处理
    print(f"  测试2: 使用预处理（CLAHE + 锐化）")
    try:
        lab = cv2.cvtColor(head_roi, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        head_roi_processed = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]]) * 0.1
        head_roi_processed = cv2.filter2D(head_roi_processed, -1, kernel)
        
        results2 = hairnet_model(head_roi_processed, conf=0.15, iou=0.45, imgsz=640, verbose=False)
        detections2 = []
        for r in results2:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    cls = int(box.cls[0])
                    if hairnet_model.names[cls] == "hairnet":
                        conf = float(box.conf[0])
                        detections2.append(conf)
        print(f"    结果: {'✅ 检测到发网' if detections2 else '❌ 未检测到'}")
        if detections2:
            print(f"    置信度: {detections2}")
    except Exception as e:
        print(f"    ❌ 预处理失败: {e}")

