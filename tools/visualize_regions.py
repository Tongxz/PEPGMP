import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Tuple

import cv2

# 确保可导入 src/*
ROOT = Path(__file__).resolve().parents[1]
# 为了支持 `from src.core.region import RegionManager`，需要把“项目根目录”加入 sys.path
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_regions(config_path: str) -> List[dict]:
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("regions", [])


def to_points_float(poly) -> List[Tuple[float, float]]:
    pts = []
    for p in poly:
        if isinstance(p, dict):
            x = p.get("x") if "x" in p else p.get("X")
            y = p.get("y") if "y" in p else p.get("Y")
            if x is None or y is None:
                continue
            try:
                xf = float(x)
                yf = float(y)
            except Exception:
                continue
            pts.append((xf, yf))
        elif isinstance(p, (list, tuple)) and len(p) >= 2:
            try:
                xf = float(p[0])
                yf = float(p[1])
            except Exception:
                continue
            pts.append((xf, yf))
    return pts


def color_for(region_type: str, name: str) -> Tuple[int, int, int]:
    # BGR
    if region_type == "handwash" or name == "洗手站立区域":
        return (0, 255, 255)  # yellow
    if name == "洗手水池":
        return (0, 215, 255)  # amber
    if region_type == "sanitize":
        return (255, 0, 255)  # magenta
    if region_type == "entrance":
        return (0, 255, 0)  # green
    if region_type == "work_area":
        return (255, 0, 0)  # blue
    return (200, 200, 200)


def draw_regions_with_region_manager(
    img,
    regions_path: str,
    ref: str = "",
    canvas: str = "",
    bg: str = "",
    fit_mode: str = "contain",
) -> None:
    import numpy as np

    from src.core.region import RegionManager

    h, w = img.shape[:2]
    rm = RegionManager()
    if not rm.load_regions_config(regions_path):
        raise SystemExit(f"Failed to load regions from {regions_path}")

    # 优先使用配置内的 meta（前端导出写入），与运行时完全一致
    if not (ref or canvas or bg):
        # 无 CLI 指示时，直接按 meta 应用
        rm.apply_mapping(w, h)
        applied = "apply_mapping(meta)"
    else:
        # CLI 指示优先（用于对比实验）
        if canvas and bg and ("x" in canvas) and ("x" in bg):
            try:
                cw, ch = map(int, canvas.lower().split("x", 1))
                bw, bh = map(int, bg.lower().split("x", 1))
                if cw > 0 and ch > 0 and bw > 0 and bh > 0:
                    rm.scale_from_canvas_and_bg(cw, ch, bw, bh, w, h, fit_mode=fit_mode)
                    applied = f"scale_from_canvas_and_bg(cw={cw},ch={ch},bw={bw},bh={bh},fit={fit_mode})"
                else:
                    rm.scale_to_frame_if_needed(w, h)
            except Exception:
                rm.scale_to_frame_if_needed(w, h)
                applied = "scale_to_frame_if_needed"
        elif ref and ("x" in ref):
            try:
                rw, rh = map(int, ref.lower().split("x", 1))
                if rw > 0 and rh > 0:
                    rm.scale_from_reference(rw, rh, w, h)
                    applied = f"scale_from_reference({rw}x{rh})"
                else:
                    rm.scale_to_frame_if_needed(w, h)
                    applied = "scale_to_frame_if_needed"
            except Exception:
                rm.scale_to_frame_if_needed(w, h)
                applied = "scale_to_frame_if_needed"
        else:
            rm.scale_to_frame_if_needed(w, h)
            applied = "scale_to_frame_if_needed"

    print(f"Region mapping applied by: {applied}")

    # 绘制区域（已缩放后的坐标）
    for r in rm.regions.values():
        rtype = r.region_type.value
        name = r.name
        pts = [(int(round(x)), int(round(y))) for (x, y) in r.polygon]
        if len(pts) < 2:
            continue
        color = color_for(rtype, name)
        arr = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(img, [arr], isClosed=True, color=color, thickness=2)
        x, y = pts[0]
        label = f"{name or rtype}"
        cv2.putText(
            img, label, (x, max(15, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2
        )


def main():
    ap = argparse.ArgumentParser(
        description="Visualize configured regions on first frame of a video"
    )
    ap.add_argument("--video", required=True, help="video file path")
    ap.add_argument(
        "--regions",
        default=os.path.join(os.getcwd(), "config", "regions.json"),
        help="regions config json",
    )
    ap.add_argument(
        "--out",
        default=os.path.join(os.getcwd(), "output", "regions_on_first_frame.jpg"),
        help="output image path",
    )
    # 对齐 demo 的坐标还原参数（可选）
    ap.add_argument(
        "--regions-ref-size",
        dest="ref",
        default="",
        help="Reference size 'WxH' used when annotating (e.g., 1280x720)",
    )
    ap.add_argument(
        "--regions-canvas-size",
        dest="canvas",
        default="",
        help="Canvas size 'WxH' used when annotating (e.g., 1280x720)",
    )
    ap.add_argument(
        "--regions-bg-size",
        dest="bg",
        default="",
        help="Background image size 'WxH' shown in canvas (e.g., 1920x1080)",
    )
    ap.add_argument(
        "--regions-fit-mode",
        dest="fit",
        default="contain",
        choices=["contain", "cover", "stretch"],
        help="How background fits in canvas",
    )
    args = ap.parse_args()

    if not os.path.exists(args.video):
        raise SystemExit(f"Video not found: {args.video}")
    if not os.path.exists(args.regions):
        raise SystemExit(f"Regions config not found: {args.regions}")

    cap = cv2.VideoCapture(args.video)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise SystemExit("Failed to read first frame")

    draw_regions_with_region_manager(
        frame,
        args.regions,
        ref=args.ref,
        canvas=args.canvas,
        bg=args.bg,
        fit_mode=args.fit,
    )

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    cv2.imwrite(args.out, frame)
    print("Saved:", args.out)


if __name__ == "__main__":
    main()
