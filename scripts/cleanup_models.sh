#!/bin/bash

################################################################################
# 模型文件清理脚本
# Purpose: 清理测试/训练模型文件，只保留生产环境必要的模型
# Usage: bash scripts/cleanup_models.sh [--dry-run] [--backup]
################################################################################

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="$PROJECT_ROOT/models"

# Parse arguments
DRY_RUN=false
BACKUP=false

for arg in "$@"; do
    case $arg in
        --dry-run|--dryrun|-n)
            DRY_RUN=true
            shift
            ;;
        --backup|-b)
            BACKUP=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--backup]"
            echo ""
            echo "Options:"
            echo "  --dry-run, -n    Show what would be deleted without actually deleting"
            echo "  --backup, -b     Create backup before deleting"
            echo "  --help, -h       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "========================================================================="
echo -e "${BLUE}模型文件清理脚本${NC}"
echo "========================================================================="
echo ""
echo "Models directory: $MODELS_DIR"
echo "Dry run: $DRY_RUN"
echo "Backup: $BACKUP"
echo ""

# Check functions
check_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

check_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

check_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

check_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Calculate sizes
calculate_size() {
    local path="$1"
    if [ -d "$path" ] || [ -f "$path" ]; then
        if [ "$(uname)" = "Darwin" ]; then
            du -sh "$path" 2>/dev/null | cut -f1
        else
            du -sh "$path" 2>/dev/null | cut -f1
        fi
    else
        echo "0"
    fi
}

# Show size info
show_size_info() {
    local path="$1"
    local size=$(calculate_size "$path")
    echo "  Size: $size"
}

# Total size to be freed
TOTAL_SIZE=0

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}将要清理的文件/目录${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 1. 训练运行文件
if [ -d "$MODELS_DIR/multi_behavior/runs" ]; then
    SIZE=$(calculate_size "$MODELS_DIR/multi_behavior/runs")
    check_warning "1. 多行为识别训练运行文件"
    echo "   Path: models/multi_behavior/runs/"
    show_size_info "$MODELS_DIR/multi_behavior/runs"
    echo "   Files: $(find "$MODELS_DIR/multi_behavior/runs" -type f 2>/dev/null | wc -l | tr -d ' ') files"
    echo ""
    TOTAL_SIZE=$((TOTAL_SIZE + $(du -sk "$MODELS_DIR/multi_behavior/runs" 2>/dev/null | cut -f1 || echo 0)))
fi

# 2. MLOps 运行文件
if [ -d "$MODELS_DIR/mlops/runs" ]; then
    SIZE=$(calculate_size "$MODELS_DIR/mlops/runs")
    check_warning "2. MLOps 训练运行文件"
    echo "   Path: models/mlops/runs/"
    show_size_info "$MODELS_DIR/mlops/runs"
    echo ""
    TOTAL_SIZE=$((TOTAL_SIZE + $(du -sk "$MODELS_DIR/mlops/runs" 2>/dev/null | cut -f1 || echo 0)))
fi

# 3. 备份文件
if [ -f "$MODELS_DIR/handwash_xgb.joblib.backup" ]; then
    SIZE=$(calculate_size "$MODELS_DIR/handwash_xgb.joblib.backup")
    check_warning "3. 洗手模型备份文件"
    echo "   Path: models/handwash_xgb.joblib.backup"
    show_size_info "$MODELS_DIR/handwash_xgb.joblib.backup"
    echo ""
    TOTAL_SIZE=$((TOTAL_SIZE + $(du -sk "$MODELS_DIR/handwash_xgb.joblib.backup" 2>/dev/null | cut -f1 || echo 0)))
fi

# 4. 系统文件
DS_STORE_COUNT=$(find "$MODELS_DIR" -name ".DS_Store" 2>/dev/null | wc -l | tr -d ' ')
if [ "$DS_STORE_COUNT" -gt 0 ]; then
    check_warning "4. macOS 系统文件"
    echo "   Path: models/**/.DS_Store"
    echo "   Files: $DS_STORE_COUNT files"
    echo ""
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}保留的必要模型${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check necessary models
check_necessary_model() {
    local path="$1"
    local name="$2"

    if [ -f "$path" ] || [ -d "$path" ]; then
        SIZE=$(calculate_size "$path")
        check_success "$name"
        echo "   Path: $path"
        echo "   Size: $SIZE"
        echo ""
        return 0
    else
        check_warning "$name (未找到)"
        echo "   Path: $path"
        echo ""
        return 1
    fi
}

check_necessary_model "$MODELS_DIR/yolo/yolov8s.pt" "YOLO 检测模型 (推荐)"
check_necessary_model "$MODELS_DIR/yolo/yolov8n.pt" "YOLO 检测模型 (轻量级)"
check_necessary_model "$MODELS_DIR/hairnet_detection/hairnet_detection.pt" "发网检测模型"
check_necessary_model "$MODELS_DIR/handwash_xgb.joblib.real" "洗手检测模型"
check_necessary_model "$MODELS_DIR/hairnet_model/weights/best.pt" "用户训练的发网模型 (可选)"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}预计释放空间${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Convert KB to human readable
if [ "$TOTAL_SIZE" -gt 0 ]; then
    if [ "$TOTAL_SIZE" -gt 1048576 ]; then
        SIZE_GB=$(echo "scale=2; $TOTAL_SIZE / 1048576" | bc)
        echo -e "${GREEN}预计释放: ${SIZE_GB}GB${NC}"
    elif [ "$TOTAL_SIZE" -gt 1024 ]; then
        SIZE_MB=$(echo "scale=2; $TOTAL_SIZE / 1024" | bc)
        echo -e "${GREEN}预计释放: ${SIZE_MB}MB${NC}"
    else
        echo -e "${GREEN}预计释放: ${TOTAL_SIZE}KB${NC}"
    fi
else
    echo -e "${YELLOW}没有找到可清理的文件${NC}"
fi

echo ""

# Confirmation
if [ "$DRY_RUN" = true ]; then
    check_info "Dry run mode: 不会实际删除文件"
    exit 0
fi

echo -e "${YELLOW}⚠️  警告: 此操作将永久删除上述文件/目录${NC}"
echo ""
read -p "确认继续? (yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    check_warning "已取消"
    exit 0
fi

echo ""

# Create backup if requested
if [ "$BACKUP" = true ]; then
    BACKUP_DIR="$PROJECT_ROOT/models_backup_$(date +%Y%m%d_%H%M%S)"
    check_info "创建备份到: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"

    if [ -d "$MODELS_DIR/multi_behavior/runs" ]; then
        cp -r "$MODELS_DIR/multi_behavior/runs" "$BACKUP_DIR/" 2>/dev/null || true
    fi

    if [ -d "$MODELS_DIR/mlops/runs" ]; then
        cp -r "$MODELS_DIR/mlops/runs" "$BACKUP_DIR/" 2>/dev/null || true
    fi

    if [ -f "$MODELS_DIR/handwash_xgb.joblib.backup" ]; then
        cp "$MODELS_DIR/handwash_xgb.joblib.backup" "$BACKUP_DIR/" 2>/dev/null || true
    fi

    check_success "备份完成: $BACKUP_DIR"
    echo ""
fi

# Cleanup
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}开始清理${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 1. Delete training runs
if [ -d "$MODELS_DIR/multi_behavior/runs" ]; then
    check_info "删除 multi_behavior/runs/ ..."
    rm -rf "$MODELS_DIR/multi_behavior/runs"
    check_success "已删除"
    echo ""
fi

# 2. Delete MLOps runs
if [ -d "$MODELS_DIR/mlops/runs" ]; then
    check_info "删除 mlops/runs/ ..."
    rm -rf "$MODELS_DIR/mlops/runs"
    check_success "已删除"
    echo ""
fi

# 3. Delete backup files
if [ -f "$MODELS_DIR/handwash_xgb.joblib.backup" ]; then
    check_info "删除 handwash_xgb.joblib.backup ..."
    rm -f "$MODELS_DIR/handwash_xgb.joblib.backup"
    check_success "已删除"
    echo ""
fi

# 4. Delete .DS_Store files
if [ "$DS_STORE_COUNT" -gt 0 ]; then
    check_info "删除 .DS_Store 文件 ..."
    find "$MODELS_DIR" -name ".DS_Store" -delete
    check_success "已删除 $DS_STORE_COUNT 个文件"
    echo ""
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}清理完成${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Show final size
FINAL_SIZE=$(du -sh "$MODELS_DIR" 2>/dev/null | cut -f1)
check_info "当前 models 目录大小: $FINAL_SIZE"

echo ""
echo "详细分析报告: docs/模型文件分析报告.md"
