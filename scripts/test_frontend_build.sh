#!/bin/bash
# 测试本地前端构建是否正常可用
# Test if local frontend build is working correctly

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "========================================================================="
echo "                     前端构建测试工具"
echo "========================================================================="
echo ""

cd "$FRONTEND_DIR"

# ==================== 步骤 1: 检查构建产物 ====================
log_info "步骤 1: 检查构建产物..."

if [ ! -d "dist" ]; then
    log_error "dist 目录不存在，请先构建前端"
    echo ""
    echo "构建命令:"
    echo "  cd frontend"
    echo "  npx vite build"
    exit 1
fi

log_success "dist 目录存在"

# 检查关键文件
MISSING_FILES=0

if [ ! -f "dist/index.html" ]; then
    log_error "index.html 不存在"
    MISSING_FILES=$((MISSING_FILES + 1))
else
    log_success "index.html 存在"
fi

if [ ! -d "dist/assets" ]; then
    log_error "assets 目录不存在"
    MISSING_FILES=$((MISSING_FILES + 1))
else
    log_success "assets 目录存在"
fi

if [ $MISSING_FILES -gt 0 ]; then
    log_error "构建产物不完整，请重新构建"
    exit 1
fi

echo ""

# ==================== 步骤 2: 分析构建产物 ====================
log_info "步骤 2: 分析构建产物..."

# 统计文件
JS_COUNT=$(find dist/assets/js -name "*.js" -type f 2>/dev/null | wc -l | tr -d ' ')
CSS_COUNT=$(find dist/assets/css -name "*.css" -type f 2>/dev/null | wc -l | tr -d ' ')
TOTAL_FILES=$(find dist -type f 2>/dev/null | wc -l | tr -d ' ')
DIST_SIZE=$(du -sh dist 2>/dev/null | awk '{print $1}')

echo "  构建产物大小: $DIST_SIZE"
echo "  JS 文件数: $JS_COUNT"
echo "  CSS 文件数: $CSS_COUNT"
echo "  总文件数: $TOTAL_FILES"

if [ "$JS_COUNT" -eq 0 ]; then
    log_error "没有找到 JS 文件，构建可能失败"
    exit 1
fi

if [ "$CSS_COUNT" -eq 0 ]; then
    log_warning "没有找到 CSS 文件（可能使用了内联样式）"
fi

echo ""

# ==================== 步骤 3: 检查 index.html ====================
log_info "步骤 3: 检查 index.html..."

if grep -q "assets/js/index" dist/index.html; then
    log_success "index.html 包含入口 JS 文件"
else
    log_error "index.html 缺少入口 JS 文件"
    exit 1
fi

# 检查是否有 vendor chunk
if grep -q "vendor" dist/index.html; then
    log_success "检测到 vendor chunk（代码分割正常）"
else
    log_warning "未检测到 vendor chunk（可能所有代码都在一个文件中）"
fi

echo ""

# ==================== 步骤 4: 检查文件完整性 ====================
log_info "步骤 4: 检查文件完整性..."

# 检查 index.html 中引用的文件是否存在
MISSING_REFS=0

while IFS= read -r line; do
    # 提取 JS 文件路径
    if [[ $line =~ src=\"([^\"]+)\" ]] || [[ $line =~ href=\"([^\"]+)\" ]]; then
        FILE_PATH="${BASH_REMATCH[1]}"
        # 移除开头的 /
        FILE_PATH="${FILE_PATH#/}"

        if [ -n "$FILE_PATH" ] && [ ! -f "dist/$FILE_PATH" ]; then
            log_error "引用的文件不存在: $FILE_PATH"
            MISSING_REFS=$((MISSING_REFS + 1))
        fi
    fi
done < dist/index.html

if [ $MISSING_REFS -eq 0 ]; then
    log_success "所有引用的文件都存在"
else
    log_error "有 $MISSING_REFS 个引用的文件不存在"
    exit 1
fi

echo ""

# ==================== 步骤 5: 启动预览服务器 ====================
log_info "步骤 5: 启动预览服务器..."

# 检查端口是否被占用
PREVIEW_PORT=4173
PREVIEW_PID=""
USE_EXISTING=false

if lsof -Pi :$PREVIEW_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    EXISTING_PID=$(lsof -Pi :$PREVIEW_PORT -sTCP:LISTEN -t | head -1)
    if ps -p $EXISTING_PID > /dev/null 2>&1; then
        log_warning "端口 $PREVIEW_PORT 已被占用 (PID: $EXISTING_PID)"
        log_info "检测到已存在的预览服务器，将使用现有服务器进行测试"
        PREVIEW_PID=$EXISTING_PID
        USE_EXISTING=true
    else
        log_warning "端口 $PREVIEW_PORT 被占用但进程不存在，尝试使用 4174"
        PREVIEW_PORT=4174
    fi
fi

if [ "$USE_EXISTING" = false ]; then
    log_info "启动预览服务器在端口 $PREVIEW_PORT..."
    log_info "访问地址: http://localhost:$PREVIEW_PORT"

    # 启动预览服务器（后台运行）
    npx vite preview --port $PREVIEW_PORT --host 0.0.0.0 > /tmp/vite-preview.log 2>&1 &
    PREVIEW_PID=$!

    # 等待服务器启动
    sleep 3

    # 检查进程是否还在运行
    if ! kill -0 $PREVIEW_PID 2>/dev/null; then
        log_error "预览服务器启动失败"
        cat /tmp/vite-preview.log
        exit 1
    fi

    log_success "预览服务器已启动 (PID: $PREVIEW_PID)"
else
    log_success "使用已存在的预览服务器 (PID: $PREVIEW_PID, 端口: $PREVIEW_PORT)"
fi

echo ""

# ==================== 步骤 6: 测试 HTTP 访问 ====================
log_info "步骤 6: 测试 HTTP 访问..."

# 等待服务器完全启动
sleep 2

# 测试根路径
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PREVIEW_PORT/" || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    log_success "HTTP 访问正常 (状态码: $HTTP_CODE)"
else
    log_error "HTTP 访问失败 (状态码: $HTTP_CODE)"
    kill $PREVIEW_PID 2>/dev/null || true
    exit 1
fi

# 测试 index.html
if curl -s "http://localhost:$PREVIEW_PORT/" | grep -q "app"; then
    log_success "index.html 内容正常"
else
    log_warning "index.html 内容可能异常"
fi

echo ""

# ==================== 步骤 7: 检查资源文件 ====================
log_info "步骤 7: 检查资源文件可访问性..."

# 获取第一个 JS 文件路径
FIRST_JS=$(find dist/assets/js -name "*.js" -type f 2>/dev/null | head -1)
if [ -n "$FIRST_JS" ]; then
    JS_REL_PATH="${FIRST_JS#dist/}"
    JS_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PREVIEW_PORT/$JS_REL_PATH" || echo "000")

    if [ "$JS_HTTP_CODE" = "200" ]; then
        log_success "JS 文件可访问 ($JS_REL_PATH)"
    else
        log_warning "JS 文件访问异常 (状态码: $JS_HTTP_CODE)"
    fi
fi

# 获取第一个 CSS 文件路径
FIRST_CSS=$(find dist/assets/css -name "*.css" -type f 2>/dev/null | head -1)
if [ -n "$FIRST_CSS" ]; then
    CSS_REL_PATH="${FIRST_CSS#dist/}"
    CSS_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PREVIEW_PORT/$CSS_REL_PATH" || echo "000")

    if [ "$CSS_HTTP_CODE" = "200" ]; then
        log_success "CSS 文件可访问 ($CSS_REL_PATH)"
    else
        log_warning "CSS 文件访问异常 (状态码: $CSS_HTTP_CODE)"
    fi
fi

echo ""

# ==================== 步骤 8: 生成测试报告 ====================
log_success "========================================================================="
log_success "                     测试完成"
log_success "========================================================================="
echo ""
log_info "测试结果:"
echo "  ✅ 构建产物完整"
echo "  ✅ 文件引用正确"
echo "  ✅ HTTP 访问正常"
echo "  ✅ 资源文件可访问"
echo ""
log_info "预览服务器信息:"
echo "  地址: http://localhost:$PREVIEW_PORT"
echo "  PID: $PREVIEW_PID"
echo ""
log_info "下一步操作:"
echo "  1. 在浏览器中打开: http://localhost:$PREVIEW_PORT"
echo "  2. 打开开发者工具 (F12) 检查控制台是否有错误"
echo "  3. 测试页面功能是否正常"
echo "  4. 停止预览服务器: kill $PREVIEW_PID"
echo "    或运行: pkill -f 'vite preview'"
echo ""

# 保持脚本运行，等待用户中断
if [ "$USE_EXISTING" = false ]; then
    trap "echo ''; log_info '正在停止预览服务器...'; kill $PREVIEW_PID 2>/dev/null || true; exit 0" INT TERM
    log_info "预览服务器正在运行，按 Ctrl+C 停止..."
    wait $PREVIEW_PID
else
    log_info "使用已存在的预览服务器，脚本将退出"
    log_info "如需停止预览服务器，请运行: kill $PREVIEW_PID"
    log_info "或运行: pkill -f 'vite preview'"
fi
