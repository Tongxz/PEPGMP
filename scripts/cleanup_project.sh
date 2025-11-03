#!/bin/bash

# 项目清理脚本
# 清理重构后的冗余文件

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================================================"
echo "                       项目清理脚本"
echo "========================================================================"
echo ""

# 显示将要清理的内容
echo -e "${BLUE}将要清理的内容：${NC}"
echo ""
echo "🗑️  阶段1：安全删除（无风险）"
echo "  • docker_backup/ - 旧Docker配置备份"
echo "  • docker_exports/ - 旧镜像导出文件（大文件）"
echo "  • how --name-only 461baf8 - 误创建的文件"
echo "  • requirements-prod.txt - 重复文件"
echo "  • config/production.env.example - 已被替代"
echo ""
echo "📦 阶段2：归档（低风险）"
echo "  • deployment/ → archive/deployment_legacy/"
echo "  • scripts/deployment/ → archive/deployment_legacy/"
echo "  • src/deployment/ → archive/deployment_legacy/"
echo ""
echo "🔄 阶段3：整理（中风险）"
echo "  • Dockerfile.prod.new → Dockerfile.prod"
echo "  • GPU性能优化README.md → docs/GPU性能优化指南.md"
echo "  • test_*.* → tools/"
echo ""
echo "预计释放空间: ~500MB - 2GB"
echo ""

# 确认
read -p "是否继续？(y/n) [n]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}已取消${NC}"
    exit 0
fi

echo ""
echo "========================================================================"
echo "开始清理..."
echo "========================================================================"
echo ""

# 计数器
deleted_files=0
moved_files=0
renamed_files=0

# ==================== 阶段1：安全删除 ====================
echo -e "${GREEN}[阶段1]${NC} 执行安全删除..."
echo ""

# 删除docker_backup/
if [ -d "docker_backup" ]; then
    echo "  删除 docker_backup/"
    rm -rf docker_backup/
    ((deleted_files++))
fi

# 删除docker_exports/
if [ -d "docker_exports" ]; then
    echo "  删除 docker_exports/"
    rm -rf docker_exports/
    ((deleted_files++))
fi

# 删除误创建文件
if [ -f "how --name-only 461baf8" ]; then
    echo "  删除 how --name-only 461baf8"
    rm -f "how --name-only 461baf8"
    ((deleted_files++))
fi

# 删除requirements-prod.txt
if [ -f "requirements-prod.txt" ]; then
    echo "  删除 requirements-prod.txt"
    rm -f requirements-prod.txt
    ((deleted_files++))
fi

# 删除config/production.env.example
if [ -f "config/production.env.example" ]; then
    echo "  删除 config/production.env.example"
    rm -f config/production.env.example
    ((deleted_files++))
fi

echo -e "${GREEN}✓${NC} 阶段1完成 (删除了 $deleted_files 个文件/目录)"
echo ""

# ==================== 阶段2：归档 ====================
echo -e "${GREEN}[阶段2]${NC} 执行归档..."
echo ""

# 创建归档目录
mkdir -p archive/deployment_legacy

# 移动deployment/
if [ -d "deployment" ]; then
    echo "  归档 deployment/ → archive/deployment_legacy/"
    mv deployment/ archive/deployment_legacy/
    ((moved_files++))
fi

# 移动scripts/deployment/
if [ -d "scripts/deployment" ]; then
    echo "  归档 scripts/deployment/ → archive/deployment_legacy/scripts_deployment/"
    mv scripts/deployment/ archive/deployment_legacy/scripts_deployment/
    ((moved_files++))
fi

# 移动src/deployment/
if [ -d "src/deployment" ]; then
    echo "  归档 src/deployment/ → archive/deployment_legacy/src_deployment/"
    mv src/deployment/ archive/deployment_legacy/src_deployment/
    ((moved_files++))
fi

echo -e "${GREEN}✓${NC} 阶段2完成 (归档了 $moved_files 个目录)"
echo ""

# ==================== 阶段3：整理 ====================
echo -e "${GREEN}[阶段3]${NC} 执行整理..."
echo ""

# 重命名Dockerfile
if [ -f "Dockerfile.prod.new" ]; then
    echo "  重命名 Dockerfile.prod.new → Dockerfile.prod"
    if [ -f "Dockerfile.prod" ]; then
        echo "    备份旧文件为 Dockerfile.prod.old"
        mv Dockerfile.prod Dockerfile.prod.old
    fi
    mv Dockerfile.prod.new Dockerfile.prod
    ((renamed_files++))
fi

# 移动GPU文档
if [ -f "GPU性能优化README.md" ]; then
    echo "  移动 GPU性能优化README.md → docs/GPU性能优化指南.md"
    mv "GPU性能优化README.md" "docs/GPU性能优化指南.md"
    ((moved_files++))
fi

# 移动测试脚本到tools/
for file in test_*.sh test_*.py test_*.js verify_*.py; do
    if [ -f "$file" ]; then
        echo "  移动 $file → tools/"
        mv "$file" tools/
        ((moved_files++))
    fi
done

echo -e "${GREEN}✓${NC} 阶段3完成 (重命名 $renamed_files 个, 移动 $moved_files 个)"
echo ""

# ==================== 总结 ====================
echo "========================================================================"
echo -e "${GREEN}✅ 清理完成${NC}"
echo "========================================================================"
echo ""
echo "统计："
echo "  • 删除: $deleted_files 个文件/目录"
echo "  • 归档: $moved_files 个目录"
echo "  • 重命名: $renamed_files 个文件"
echo ""
echo "归档位置: archive/deployment_legacy/"
echo ""

# 显示磁盘空间变化
echo "当前项目大小:"
du -sh . 2>/dev/null || echo "  无法计算（权限限制）"
echo ""

echo "📝 建议的后续操作："
echo "  1. 验证应用仍可正常启动"
echo "  2. 运行测试: pytest tests/"
echo "  3. 提交更改: git add . && git commit -m 'chore: 清理冗余文件'"
echo ""
echo "🔙 如需回滚："
echo "  从archive/恢复: cp -r archive/deployment_legacy/deployment/ ./"
echo "  或使用Git: git reset --hard HEAD~1"
echo ""
