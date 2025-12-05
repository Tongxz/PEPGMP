#!/bin/bash

# 模型下载脚本
# 用途: 从远程URL下载模型文件，支持校验
# 使用: bash scripts/download_models.sh [目标目录]

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 配置
TARGET_DIR="${1:-./models}"
MODELS_CONFIG="${2:-./config/models.json}"

# 示例模型列表（实际使用时建议从配置文件读取）
# 格式: "模型名|URL|MD5"
# 这里使用占位符URL，实际部署时请替换为真实的对象存储URL
DEFAULT_MODELS=(
    "yolo_hairnet.pt|https://example.com/models/yolo_hairnet_v1.pt|d41d8cd98f00b204e9800998ecf8427e"
    "yolo_person.pt|https://example.com/models/yolo_person_v2.pt|d41d8cd98f00b204e9800998ecf8427e"
)

echo "========================================================================="
echo "                     模型下载管理器"
echo "========================================================================="
echo "目标目录: $TARGET_DIR"
echo ""

mkdir -p "$TARGET_DIR"

# 检查是否安装了wget
if ! command -v wget &> /dev/null; then
    echo -e "${RED}错误: 未安装wget${NC}"
    exit 1
fi

# 下载函数
download_model() {
    local name=$1
    local url=$2
    local checksum=$3
    local file_path="$TARGET_DIR/$name"

    echo "检查模型: $name"

    # 检查文件是否存在且校验和匹配
    if [ -f "$file_path" ]; then
        echo "  文件已存在，检查完整性..."
        # macOS使用md5，Linux使用md5sum
        if command -v md5sum &> /dev/null; then
            local current_sum=$(md5sum "$file_path" | awk '{print $1}')
        else
            local current_sum=$(md5 -q "$file_path")
        fi

        if [ "$current_sum" == "$checksum" ]; then
            echo -e "  ${GREEN}✅ 校验通过，跳过下载${NC}"
            return 0
        else
            echo -e "  ${YELLOW}⚠️  校验失败 (当前: $current_sum, 期望: $checksum)，重新下载...${NC}"
        fi
    else
        echo "  文件不存在，准备下载..."
    fi

    # 下载文件
    echo "  下载中: $url"
    if wget -q --show-progress -O "$file_path" "$url"; then
        echo -e "  ${GREEN}✅ 下载成功${NC}"
    else
        echo -e "  ${RED}❌ 下载失败${NC}"
        return 1
    fi
}

# 主循环
echo "开始处理模型列表..."
echo ""

# 这里简单处理，实际项目可以解析 JSON 配置文件
for model_info in "${DEFAULT_MODELS[@]}"; do
    IFS="|" read -r name url checksum <<< "$model_info"

    # 如果是示例URL，跳过
    if [[ "$url" == *"example.com"* ]]; then
        echo -e "${YELLOW}跳过示例模型: $name (请配置真实URL)${NC}"
        continue
    fi

    download_model "$name" "$url" "$checksum"
done

echo ""
echo "========================================================================="
echo "                     处理完成"
echo "========================================================================="
