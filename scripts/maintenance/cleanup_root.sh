#!/bin/bash

set -euo pipefail

# 根目录安全清理脚本（默认 dry-run）
# - 仅移动，不删除；避免覆盖（目标存在则追加时间戳）
# - 分类：模型权重、日志、临时/预览图片、散落测试图片

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DRY_RUN=1
if [[ "${1:-}" == "--apply" ]]; then
  DRY_RUN=0
fi

timestamp() { date +%Y%m%d_%H%M%S; }
ensure_dir() { [[ -d "$1" ]] || { echo "[MKDIR] $1"; [[ $DRY_RUN -eq 1 ]] || mkdir -p "$1"; }; }
move_safe() {
  local src="$1" dst="$2"
  if [[ ! -f "$src" ]]; then return; fi
  ensure_dir "$(dirname "$dst")"
  if [[ -f "$dst" ]]; then
    local base="${dst%.*}" ext=".${dst##*.}" ts="$(timestamp)"
    dst="${base}_${ts}${ext}"
  fi
  echo "[MOVE] $src -> $dst"
  [[ $DRY_RUN -eq 1 ]] || mv "$src" "$dst"
}

echo "Project root: $ROOT_DIR"
echo "Mode: $([[ $DRY_RUN -eq 1 ]] && echo 'DRY-RUN' || echo 'APPLY')"

# 1) 模型权重：根目录的 yolov*.pt 移入 models/yolo/
ensure_dir "models/yolo"
for f in yolov8n.pt yolov8s.pt yolov8m.pt yolov8l.pt yolo11n.pt; do
  [[ -f "$f" ]] && move_safe "$f" "models/yolo/$f"
done

# 2) 日志：app.log -> logs/app.log
ensure_dir "logs"
[[ -f app.log ]] && move_safe "app.log" "logs/app.log"

# 3) 预览/演示图片：realistic_*.* -> docs/assets/ 或 output/
ensure_dir "docs/assets"
for f in realistic_test_image.jpg realistic_test_preview.png; do
  [[ -f "$f" ]] && move_safe "$f" "docs/assets/$f"
done

# 4) 散落测试图片：test_*.jpg|png -> tests/fixtures/images/
ensure_dir "tests/fixtures/images"
for f in test_image.jpg test_image.png test_person_image.jpg test_light_blue_hairnet.jpg test_mediapipe_annotated.png test_mediapipe_integration.png; do
  [[ -f "$f" ]] && move_safe "$f" "tests/fixtures/images/$f"
done

echo "Done. (Use --apply to execute moves)"
