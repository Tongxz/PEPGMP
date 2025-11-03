#!/bin/bash

# 深度清理脚本 - 清理重构后遗留代码
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

# 获取阶段参数
STAGE=${1:-all}

echo "========================================================================"
echo "                     深度清理脚本 - 重构遗留代码"
echo "========================================================================"
echo ""

# 显示将要清理的内容
echo -e "${BLUE}清理阶段: $STAGE${NC}"
echo ""

if [ "$STAGE" = "all" ] || [ "$STAGE" = "1" ]; then
    echo "🗑️  阶段1：安全删除（高优先级）"
    echo "  • archive/ - 所有已归档代码"
    echo "  • examples/ 中的过时示例（4个文件）"
    echo "  • Dockerfile.prod.old - 旧Dockerfile备份"
    echo "  • __pycache__/ - Python缓存"
    echo ""
fi

if [ "$STAGE" = "all" ] || [ "$STAGE" = "2" ]; then
    echo "⚠️  阶段2：检查后删除（中优先级）"
    echo "  • 检查detection_service_di.py使用情况"
    echo "  • 评估测试工具文件"
    echo "  • 对比requirements文件"
    echo ""
fi

if [ "$STAGE" = "all" ] || [ "$STAGE" = "3" ]; then
    echo "📝 阶段3：整理优化（低优先级）"
    echo "  • 清理.pyc文件"
    echo "  • 清理模型备份"
    echo ""
fi

# 确认
if [ "$STAGE" != "check" ]; then
    read -p "是否继续？(y/n) [n]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}已取消${NC}"
        exit 0
    fi
fi

echo ""
echo "========================================================================"
echo "开始执行..."
echo "========================================================================"
echo ""

# 计数器
deleted_files=0
deleted_dirs=0

# ==================== 阶段1：安全删除 ====================
if [ "$STAGE" = "all" ] || [ "$STAGE" = "1" ]; then
    echo -e "${GREEN}[阶段1]${NC} 执行安全删除..."
    echo ""
    
    # 删除archive目录
    if [ -d "archive" ]; then
        echo "  删除 archive/ (所有已归档代码)"
        du -sh archive/ 2>/dev/null || true
        rm -rf archive/
        ((deleted_dirs++))
    fi
    
    # 删除过时的examples
    echo "  清理 examples/ 目录..."
    for file in examples/demo_camera_direct.py \
                examples/example_usage.py \
                examples/integrate_yolo_detector.py \
                examples/use_yolo_hairnet_detector.py; do
        if [ -f "$file" ]; then
            echo "    删除 $file"
            rm -f "$file"
            ((deleted_files++))
        fi
    done
    
    # 删除Dockerfile.prod.old
    if [ -f "Dockerfile.prod.old" ]; then
        echo "  删除 Dockerfile.prod.old"
        rm -f Dockerfile.prod.old
        ((deleted_files++))
    fi
    
    # 清理__pycache__
    echo "  清理 __pycache__/ 目录..."
    pycache_count=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
    if [ $pycache_count -gt 0 ]; then
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        echo "    删除 $pycache_count 个 __pycache__ 目录"
        deleted_dirs=$((deleted_dirs + pycache_count))
    fi
    
    echo -e "${GREEN}✓${NC} 阶段1完成 (删除 $deleted_files 个文件, $deleted_dirs 个目录)"
    echo ""
fi

# ==================== 阶段2：检查后删除 ====================
if [ "$STAGE" = "all" ] || [ "$STAGE" = "2" ]; then
    echo -e "${GREEN}[阶段2]${NC} 检查并清理..."
    echo ""
    
    # 检查detection_service_di.py的使用
    if [ -f "src/services/detection_service_di.py" ]; then
        echo "  检查 detection_service_di.py 使用情况..."
        ref_count=$(grep -r "detection_service_di" --include="*.py" src/ tests/ main.py 2>/dev/null | grep -v "detection_service_di.py:" | wc -l || echo 0)
        echo "    找到 $ref_count 处引用"
        
        if [ $ref_count -eq 0 ]; then
            echo "    未找到实际使用，删除文件"
            rm -f src/services/detection_service_di.py
            ((deleted_files++))
        else
            echo -e "    ${YELLOW}发现引用，保留文件${NC}"
            echo "    如需查看引用位置，运行:"
            echo "    grep -rn 'detection_service_di' --include='*.py' src/ tests/ main.py"
        fi
    fi
    
    # 检查测试工具
    echo "  检查测试工具文件..."
    if [ -f "tools/test_mlops_integration.py" ]; then
        echo "    检查 test_mlops_integration.py"
        # 如果没有被CI使用，可以移动到archive
        echo -e "    ${YELLOW}保留，建议手动评估${NC}"
    fi
    
    # 对比requirements文件
    if [ -f "requirements.prod.txt" ] && [ -f "requirements.txt" ]; then
        echo "  对比 requirements文件..."
        if diff -q requirements.txt requirements.prod.txt > /dev/null 2>&1; then
            echo "    文件内容一致，删除 requirements.prod.txt"
            rm -f requirements.prod.txt
            ((deleted_files++))
        else
            echo -e "    ${YELLOW}文件内容不同，保留${NC}"
            echo "    运行 'diff requirements.txt requirements.prod.txt' 查看差异"
        fi
    fi
    
    echo -e "${GREEN}✓${NC} 阶段2完成"
    echo ""
fi

# ==================== 阶段3：整理优化 ====================
if [ "$STAGE" = "all" ] || [ "$STAGE" = "3" ]; then
    echo -e "${GREEN}[阶段3]${NC} 整理优化..."
    echo ""
    
    # 清理.pyc文件
    echo "  清理 .pyc 和 .pyo 文件..."
    pyc_count=$(find . -type f \( -name "*.pyc" -o -name "*.pyo" \) 2>/dev/null | wc -l)
    if [ $pyc_count -gt 0 ]; then
        find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true
        echo "    删除 $pyc_count 个 Python 缓存文件"
        deleted_files=$((deleted_files + pyc_count))
    fi
    
    # 检查模型备份
    if ls models/*.backup 2>/dev/null; then
        echo "  发现模型备份文件:"
        ls -lh models/*.backup
        echo -e "  ${YELLOW}建议手动验证后删除${NC}"
    fi
    
    echo -e "${GREEN}✓${NC} 阶段3完成"
    echo ""
fi

# ==================== 检查模式 ====================
if [ "$STAGE" = "check" ]; then
    echo -e "${BLUE}[检查模式]${NC} 分析项目..."
    echo ""
    
    echo "📊 可清理项目:"
    echo ""
    
    # Archive目录
    if [ -d "archive" ]; then
        size=$(du -sh archive/ 2>/dev/null | cut -f1)
        echo "  ✓ archive/ ($size)"
    fi
    
    # Examples
    count=0
    for file in examples/demo_camera_direct.py \
                examples/example_usage.py \
                examples/integrate_yolo_detector.py \
                examples/use_yolo_hairnet_detector.py; do
        [ -f "$file" ] && ((count++))
    done
    [ $count -gt 0 ] && echo "  ✓ examples/ 中的 $count 个过时文件"
    
    # Backup文件
    [ -f "Dockerfile.prod.old" ] && echo "  ✓ Dockerfile.prod.old"
    
    # __pycache__
    pycache_count=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
    [ $pycache_count -gt 0 ] && echo "  ✓ $pycache_count 个 __pycache__ 目录"
    
    # .pyc文件
    pyc_count=$(find . -type f \( -name "*.pyc" -o -name "*.pyo" \) 2>/dev/null | wc -l)
    [ $pyc_count -gt 0 ] && echo "  ✓ $pyc_count 个 .pyc/.pyo 文件"
    
    echo ""
    echo "运行清理:"
    echo "  ./scripts/deep_cleanup.sh 1    # 仅阶段1"
    echo "  ./scripts/deep_cleanup.sh all  # 全部阶段"
    echo ""
    exit 0
fi

# ==================== 总结 ====================
echo "========================================================================"
echo -e "${GREEN}✅ 清理完成${NC}"
echo "========================================================================"
echo ""
echo "统计："
echo "  • 删除文件: $deleted_files"
echo "  • 删除目录: $deleted_dirs"
echo ""

# 显示当前项目大小
echo "当前项目大小:"
du -sh . 2>/dev/null || echo "  无法计算"
echo ""

echo "📝 建议的后续操作："
echo "  1. 验证应用启动: ./scripts/start_dev.sh"
echo "  2. 运行测试: pytest tests/ -v"
echo "  3. 提交更改: git add . && git commit -m 'chore: 深度清理重构遗留代码'"
echo ""

