#!/bin/bash
# 生产环境解压脚本（Linux版本）

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}生产环境解压脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查参数
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ 请指定包文件路径${NC}"
    echo -e "${YELLOW}用法: $0 <包文件路径> [目标目录]${NC}"
    echo -e "${YELLOW}示例: $0 /media/user/Untitled/imag/pyt_production_20251020_114324.tar.gz /opt/pyt_production${NC}"
    exit 1
fi

PACKAGE_FILE="$1"
TARGET_DIR="${2:-/opt/pyt_production}"

echo -e "${GREEN}包文件: ${PACKAGE_FILE}${NC}"
echo -e "${GREEN}目标目录: ${TARGET_DIR}${NC}"

# 检查包文件是否存在
if [ ! -f "${PACKAGE_FILE}" ]; then
    echo -e "${RED}❌ 包文件不存在: ${PACKAGE_FILE}${NC}"
    exit 1
fi

# 创建目标目录
echo -e "\n${GREEN}[1/3] 创建目标目录${NC}"
mkdir -p "${TARGET_DIR}"
cd "${TARGET_DIR}"

# 解压包文件（使用--warning=no-unknown-keyword忽略警告）
echo -e "\n${GREEN}[2/3] 解压包文件${NC}"
echo -e "${YELLOW}正在解压，请稍候...${NC}"
tar --warning=no-unknown-keyword -xzf "${PACKAGE_FILE}" 2>&1 | grep -v "LIBARCHIVE" || true

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 解压成功${NC}"
else
    echo -e "${RED}❌ 解压失败${NC}"
    exit 1
fi

# 修复权限
echo -e "\n${GREEN}[3/3] 修复权限${NC}"
EXTRACTED_DIR=$(ls -td pyt_production_* | head -1)
if [ -d "${EXTRACTED_DIR}" ]; then
    cd "${EXTRACTED_DIR}"

    # 修复目录权限（递归）
    echo -e "${YELLOW}修复目录权限...${NC}"
    find . -type d -exec chmod 755 {} \;

    # 修复文件权限（递归）
    echo -e "${YELLOW}修复文件权限...${NC}"
    find . -type f -exec chmod 644 {} \;

    # 修复脚本权限（递归）
    echo -e "${YELLOW}修复脚本权限...${NC}"
    find . -name "*.sh" -exec chmod +x {} \;

    # 修复Python脚本权限
    echo -e "${YELLOW}修复Python脚本权限...${NC}"
    find . -name "*.py" -exec chmod +x {} \;

    # 特别修复scripts目录权限
    if [ -d "scripts" ]; then
        echo -e "${YELLOW}特别修复scripts目录权限...${NC}"
        chmod -R 755 scripts/
        find scripts/ -type f -exec chmod 644 {} \;
        find scripts/ -name "*.sh" -exec chmod +x {} \;
        find scripts/ -name "*.py" -exec chmod +x {} \;
    fi

    echo -e "${GREEN}✅ 权限修复完成${NC}"
else
    echo -e "${RED}❌ 未找到解压目录${NC}"
    exit 1
fi

# 完成
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 解压完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}解压目录: ${TARGET_DIR}/${EXTRACTED_DIR}${NC}"
echo -e "${GREEN}========================================${NC}"

# 显示目录内容
echo -e "\n${GREEN}目录内容:${NC}"
ls -lh

# 下一步提示
echo -e "\n${YELLOW}下一步:${NC}"
echo -e "${YELLOW}cd ${TARGET_DIR}/${EXTRACTED_DIR}${NC}"
echo -e "${YELLOW}docker load -i images/pyt-api-prod.tar${NC}"
echo -e "${YELLOW}docker load -i images/pyt-frontend-prod.tar${NC}"
echo -e "${YELLOW}chmod +x scripts/deployment/start_production.sh${NC}"
echo -e "${YELLOW}./scripts/deployment/start_production.sh${NC}"
