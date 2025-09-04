import os
import json
import argparse
import cv2
from typing import List, Tuple


def load_regions(config_path: str) -> List[dict]:
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('regions', [])


def to_points_float(poly) -> List[Tuple[float, float]]:
    pts = []
    for p in poly:
        if isinstance(p, dict):
            x = p.get('x') if 'x' in p else p.get('X')
            y = p.get('y') if 'y' in p else p.get('Y')
            if x is None or y is None:
                continue
            try:
                xf = float(x); yf = float(y)
            except Exception:
                continue
            pts.append((xf, yf))
        elif isinstance(p, (list, tuple)) and len(p) >= 2:
            try:
                xf = float(p[0]); yf = float(p[1])
            except Exception:
                continue
            pts.append((xf, yf))
    return pts


def color_for(region_type: str, name: str) -> Tuple[int, int, int]:
    # BGR
    if region_type == 'handwash' or name == '洗手站立区域':
        return (0, 255, 255)  # yellow
    if name == '洗手水池':
        return (0, 215, 255)  # amber
    if region_type == 'sanitize':
        return (255, 0, 255)  # magenta
    if region_type == 'entrance':
        return (0, 255, 0)  # green
    if region_type == 'work_area':
        return (255, 0, 0)  # blue
    return (200, 200, 200)


def draw_regions(img, regions: List[dict]) -> None:
    import numpy as np
    h, w = img.shape[:2]
    # 收集所有点判断参考尺寸/是否需要缩放
    all_pts = []
    parsed = []
    for r in regions:
        poly = r.get('polygon') or r.get('points') or []
        pts = to_points_float(poly)
        parsed.append((r, pts))
        all_pts.extend(pts)
    sx = sy = 1.0
    if all_pts:
        maxx = max(p[0] for p in all_pts)
        maxy = max(p[1] for p in all_pts)
        minx = min(p[0] for p in all_pts)
        miny = min(p[1] for p in all_pts)
        # 归一化坐标 [0,1] → 放大到帧
        if 0.0 <= minx and 0.0 <= miny and maxx <= 1.0 and maxy <= 1.0:
            sx, sy = float(w), float(h)
        else:
            # 若超出帧大小，按轴向比例缩放到帧
            if maxx > w * 1.02 or maxy > h * 1.02:
                sx = (w / maxx) if maxx > 0 else 1.0
                sy = (h / maxy) if maxy > 0 else 1.0
        print(f"Region scale factors: sx={sx:.4f}, sy={sy:.4f} (frame={w}x{h}, max=({maxx:.1f},{maxy:.1f}))")

    # 绘制（应用缩放）
    for r, pts in parsed:
        rtype = r.get('region_type') or r.get('type')
        name = r.get('name', '')
        if len(pts) < 2:
            continue
        scaled = [(int(round(x*sx)), int(round(y*sy))) for x, y in pts]
        color = color_for(rtype, name)
        arr = np.array(scaled, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(img, [arr], isClosed=True, color=color, thickness=2)
        x, y = scaled[0]
        label = f"{name or rtype}"
        cv2.putText(img, label, (x, max(15, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


def main():
    ap = argparse.ArgumentParser(description='Visualize configured regions on first frame of a video')
    ap.add_argument('--video', required=True, help='video file path')
    ap.add_argument('--regions', default=os.path.join(os.getcwd(), 'config', 'regions.json'), help='regions config json')
    ap.add_argument('--out', default=os.path.join(os.getcwd(), 'output', 'regions_on_first_frame.jpg'), help='output image path')
    args = ap.parse_args()

    if not os.path.exists(args.video):
        raise SystemExit(f'Video not found: {args.video}')
    if not os.path.exists(args.regions):
        raise SystemExit(f'Regions config not found: {args.regions}')

    cap = cv2.VideoCapture(args.video)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise SystemExit('Failed to read first frame')

    regions = load_regions(args.regions)
    draw_regions(frame, regions)

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    cv2.imwrite(args.out, frame)
    print('Saved:', args.out)


if __name__ == '__main__':
    main()


