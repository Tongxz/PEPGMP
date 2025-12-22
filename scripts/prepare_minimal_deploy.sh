#!/bin/bash
# 准备最小化部署包（仅运行必需文件），支持增量同步与强制覆盖，所有提示与注释均为中文。

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_DIR="${1:-$HOME/projects/PEPGMP}"   # 目标部署目录
FORCE_OVERWRITE="${2:-no}"                  # 是否强制覆盖 yes/no

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
STEP=0; TOTAL_STEPS=8

print_step(){ STEP=$((STEP+1)); echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BLUE}[步骤 $STEP/$TOTAL_STEPS]${NC} $1"; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
print_info(){ echo -e "${BLUE}[信息]${NC} $1"; }
print_success(){ echo -e "${GREEN}[完成]${NC} $1"; }
print_warning(){ echo -e "${YELLOW}[警告]${NC} $1"; }
print_error(){ echo -e "${RED}[错误]${NC} $1"; }

echo "========================================================================="
echo "                      准备最小化部署包"
echo "========================================================================="
echo "源码目录：$PROJECT_ROOT"
echo "部署目录：$DEPLOY_DIR"
echo "强制覆盖：$FORCE_OVERWRITE"
echo ""

# 判断文件是否需要更新（md5/shasum/diff/大小）
file_needs_update() {
    local src_file="$1" dst_file="$2"
    [ ! -f "$dst_file" ] && return 0
    [[ "$FORCE_OVERWRITE" =~ ^(yes|y)$ ]] && return 0

    if command -v md5sum >/dev/null 2>&1; then
        src_hash=$(md5sum "$src_file" | cut -d' ' -f1); dst_hash=$(md5sum "$dst_file" | cut -d' ' -f1)
        [ "$src_hash" != "$dst_hash" ] && return 0 || return 1
    elif command -v md5 >/dev/null 2>&1; then
        src_hash=$(md5 -q "$src_file"); dst_hash=$(md5 -q "$dst_file")
        [ "$src_hash" != "$dst_hash" ] && return 0 || return 1
    elif command -v shasum >/dev/null 2>&1; then
        src_hash=$(shasum "$src_file" | cut -d' ' -f1); dst_hash=$(shasum "$dst_file" | cut -d' ' -f1)
        [ "$src_hash" != "$dst_hash" ] && return 0 || return 1
    elif command -v diff >/dev/null 2>&1; then
        diff -q "$src_file" "$dst_file" >/dev/null 2>&1 || return 0; return 1
    fi

    if [ "$(uname)" = "Darwin" ]; then src_size=$(stat -f%z "$src_file"); dst_size=$(stat -f%z "$dst_file"); else src_size=$(stat -c%s "$src_file"); dst_size=$(stat -c%s "$dst_file"); fi
    [ "$src_size" != "$dst_size" ] && return 0 || return 1
}

# 复制单文件（带差异判断）
safe_copy_file() {
    local src_file="$1" dst_file="$2" description="${3:-file}"
    if [ ! -f "$src_file" ]; then print_warning "源文件不存在: $src_file"; return 1; fi
    if file_needs_update "$src_file" "$dst_file"; then
        mkdir -p "$(dirname "$dst_file")"; cp "$src_file" "$dst_file"; print_success "已更新: $description"
    else
        print_info "跳过: $description（无变化）"
    fi
}

# 复制目录（优先 rsync 增量）
safe_copy_dir() {
    local src_dir="$1" dst_dir="$2" description="${3:-directory}"
    [ ! -d "$src_dir" ] && print_warning "源目录不存在: $src_dir" && return 1
    if [ -z "$(ls -A "$src_dir" 2>/dev/null)" ]; then print_info "源目录为空: $src_dir"; mkdir -p "$dst_dir"; return 0; fi

    if [ ! -d "$dst_dir" ] || [[ "$FORCE_OVERWRITE" =~ ^(yes|y)$ ]]; then
        mkdir -p "$(dirname "$dst_dir")"; cp -r "$src_dir" "$(dirname "$dst_dir")/"; print_success "已更新: $description"; return 0
    fi

    if command -v rsync >/dev/null 2>&1; then
        changes=$(rsync -avnc --delete "$src_dir/" "$dst_dir/" 2>/dev/null | grep -c "^[^>]" || echo "0")
        if [ "$changes" -gt 2 ]; then rsync -av --delete "$src_dir/" "$dst_dir/" >/dev/null 2>&1; print_success "已更新: $description（rsync 增量）"; else print_info "跳过: $description（未检测到变化）"; fi
        return 0
    fi

    src_count=$(find "$src_dir" -type f | wc -l | tr -d ' '); dst_count=$(find "$dst_dir" -type f 2>/dev/null | wc -l | tr -d ' ')
    if [ "$(uname)" = "Darwin" ]; then src_size=$(du -sk "$src_dir" | cut -f1); dst_size=$(du -sk "$dst_dir" 2>/dev/null | cut -f1); else src_size=$(du -s "$src_dir" | cut -f1); dst_size=$(du -s "$dst_dir" 2>/dev/null | cut -f1); fi
    if [ "$src_count" -ne "$dst_count" ] || [ "$src_size" -ne "$dst_size" ]; then
        mkdir -p "$(dirname "$dst_dir")"; rm -rf "$dst_dir"; cp -r "$src_dir" "$(dirname "$dst_dir")/"; print_success "已更新: $description（文件/大小有变）"
    else
        print_info "跳过: $description（无变化）"
    fi
}

# 1. 创建目录
print_step "创建目录结构"
print_info "目标目录：$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"/{config,models,data,logs,scripts,nginx/ssl,frontend/dist}
print_success "目录结构已创建/存在"

# 2. 复制 docker-compose（优先 1Panel 版本）
print_step "复制 Docker Compose 文件"
if [ -f "$PROJECT_ROOT/docker-compose.prod.1panel.yml" ]; then
    print_info "使用 1Panel 版本（无 build，使用已导入镜像）"
    safe_copy_file "$PROJECT_ROOT/docker-compose.prod.1panel.yml" "$DEPLOY_DIR/docker-compose.prod.yml" "docker-compose.prod.yml（1Panel）"
else
    print_warning "未找到 1Panel 版本，改用标准 docker-compose.prod.yml（如含 build 请手动移除）"
    safe_copy_file "$PROJECT_ROOT/docker-compose.prod.yml" "$DEPLOY_DIR/docker-compose.prod.yml" "docker-compose.prod.yml"
fi

# 3. 复制 config/
print_step "复制配置目录 config/"
safe_copy_dir "$PROJECT_ROOT/config" "$DEPLOY_DIR/config" "config/"

# 4. 复制 models/（支持增量）
print_step "复制模型目录 models/"
if [ -d "$PROJECT_ROOT/models" ] && [ -n "$(ls -A "$PROJECT_ROOT/models" 2>/dev/null)" ]; then
    MODEL_COUNT=$(find "$PROJECT_ROOT/models" -type f | wc -l | tr -d ' ')
    TOTAL_SIZE=$(du -sh "$PROJECT_ROOT/models" 2>/dev/null | cut -f1)
    print_info "模型文件数: $MODEL_COUNT，总大小: $TOTAL_SIZE"

    if [ ! -d "$DEPLOY_DIR/models" ] || [[ "$FORCE_OVERWRITE" =~ ^(yes|y)$ ]]; then
        print_info "全量复制模型..."
        if command -v rsync >/dev/null 2>&1; then
            rsync -av --info=progress2 "$PROJECT_ROOT/models/" "$DEPLOY_DIR/models/" 2>&1 | while IFS= read -r line; do echo -ne "\r${BLUE}[信息]${NC} $line"; done; echo ""
        else
            cp -r "$PROJECT_ROOT/models" "$(dirname "$DEPLOY_DIR/models")/"
        fi
        print_success "模型目录复制完成"
    else
        print_info "增量模式：检测新增模型..."
        NEW_MODELS=()
        while IFS= read -r -d '' file; do rel_path="${file#$PROJECT_ROOT/models/}"; [ ! -f "$DEPLOY_DIR/models/$rel_path" ] && NEW_MODELS+=("$rel_path"); done < <(find "$PROJECT_ROOT/models" -type f -print0 2>/dev/null)
        if [ ${#NEW_MODELS[@]} -gt 0 ]; then
            echo ""; print_warning "发现 ${#NEW_MODELS[@]} 个新增模型："; for m in "${NEW_MODELS[@]}"; do echo "  - $m"; done
            read -p "是否复制这些新增模型到部署目录? (y/N): " -n 1 -r; echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                for m in "${NEW_MODELS[@]}"; do mkdir -p "$(dirname "$DEPLOY_DIR/models/$m")"; cp "$PROJECT_ROOT/models/$m" "$DEPLOY_DIR/models/$m"; print_success "已复制: $m"; done
            else
                print_info "已跳过新增模型复制"
            fi
        else
            print_info "未发现新增模型"
        fi
        if command -v rsync >/dev/null 2>&1; then
            CHANGES=$(rsync -avnc --delete "$PROJECT_ROOT/models/" "$DEPLOY_DIR/models/" 2>/dev/null | grep -c "^[^>]" || echo "0")
            [ "$CHANGES" -gt 2 ] && print_warning "检测到已存在模型有变化，如需覆盖请使用强制模式"
        fi
    fi
else
    print_warning "models/ 为空或不存在，已创建空目录"
    mkdir -p "$DEPLOY_DIR/models"
fi

# 5. 准备 Nginx 与前端挂载目录
print_step "准备 Nginx 配置与前端目录"
print_info "确保 nginx 目录结构存在"
mkdir -p "$PROJECT_ROOT/nginx/ssl"

FRONTEND_DIST_TARGET="$DEPLOY_DIR/frontend/dist"
print_info "Scheme B：frontend-init 启动时会解压静态文件，需保证挂载目录存在"
mkdir -p "$FRONTEND_DIST_TARGET"

if [ -d "$PROJECT_ROOT/frontend/dist" ] && [ -f "$PROJECT_ROOT/frontend/dist/index.html" ]; then
    SOURCE_FILE_COUNT=$(find "$PROJECT_ROOT/frontend/dist" -type f | wc -l)
    print_info "发现源码静态文件，预填充 $SOURCE_FILE_COUNT 个文件（frontend-init 如需会覆盖）"
    if [[ "$FORCE_OVERWRITE" =~ ^(yes|y)$ ]] || [ ! -f "$FRONTEND_DIST_TARGET/index.html" ]; then
        cp -r "$PROJECT_ROOT/frontend/dist"/* "$FRONTEND_DIST_TARGET/" 2>/dev/null || print_warning "复制静态文件失败（非致命，frontend-init 会处理）"
        print_success "前端静态文件已预填充"
    else
        print_info "目标已有静态文件，跳过预填充"
    fi
else
    print_info "源码未检测到静态文件，frontend-init 首次启动会自动解压"
fi

print_info "清理部署目录中错误的 nginx 结构（如有）"
if [ -d "$DEPLOY_DIR/nginx/nginx.conf" ]; then
    sudo rm -rf "$DEPLOY_DIR/nginx/nginx.conf" 2>/dev/null || rm -rf "$DEPLOY_DIR/nginx/nginx.conf"
fi

if [ -d "$DEPLOY_DIR/nginx" ]; then
    CURRENT_USER=$(whoami)
    sudo chown -R "$CURRENT_USER:$CURRENT_USER" "$DEPLOY_DIR/nginx/" 2>/dev/null || chown -R "$CURRENT_USER:$CURRENT_USER" "$DEPLOY_DIR/nginx/" 2>/dev/null || true
fi

print_info "复制 nginx 配置..."
safe_copy_dir "$PROJECT_ROOT/nginx" "$DEPLOY_DIR/nginx" "nginx 配置目录"
if [ -f "$DEPLOY_DIR/nginx/nginx.conf" ]; then
    chmod 644 "$DEPLOY_DIR/nginx/nginx.conf"; CURRENT_USER=$(whoami); chown "$CURRENT_USER:$CURRENT_USER" "$DEPLOY_DIR/nginx/nginx.conf" 2>/dev/null || true
    print_success "nginx.conf 权限已设置"
else
    print_error "nginx.conf 复制失败"
fi

# 6. 复制部署脚本
print_step "复制部署脚本"
safe_copy_file "$PROJECT_ROOT/scripts/generate_production_config.sh" "$DEPLOY_DIR/scripts/generate_production_config.sh" "generate_production_config.sh"
safe_copy_file "$PROJECT_ROOT/scripts/init_db.sql" "$DEPLOY_DIR/scripts/init_db.sql" "init_db.sql"
if [ ! -f "$PROJECT_ROOT/scripts/docker-entrypoint.sh" ]; then print_error "缺少 scripts/docker-entrypoint.sh（API 启动必需）"; exit 1; fi
safe_copy_file "$PROJECT_ROOT/scripts/docker-entrypoint.sh" "$DEPLOY_DIR/scripts/docker-entrypoint.sh" "docker-entrypoint.sh"
safe_copy_file "$PROJECT_ROOT/scripts/import_images_from_windows.sh" "$DEPLOY_DIR/scripts/import_images_from_windows.sh" "import_images_from_windows.sh"
safe_copy_file "$PROJECT_ROOT/scripts/update_image_version.sh" "$DEPLOY_DIR/scripts/update_image_version.sh" "update_image_version.sh"
for script in "$DEPLOY_DIR/scripts/"*.sh; do [ -f "$script" ] && chmod +x "$script"; done
print_success "部署脚本复制并赋权完成"

# 7. 处理环境变量文件
print_step "处理环境配置 .env.production"
if [ ! -f "$DEPLOY_DIR/.env.production" ]; then
    print_warning ".env.production 不存在，可选择立即生成"
    echo "  ✓ 生成 .env.production 与 .env.production.credentials"
    echo "  ✓ 自动生成强口令并设置权限"
    read -p "$(echo -e ${YELLOW}是否现在生成配置? [y/N] ${NC})" run_generate
    if [[ $run_generate =~ ^[Yy]$ ]]; then
        cd "$DEPLOY_DIR"
        if [ -f "scripts/generate_production_config.sh" ]; then
            bash scripts/generate_production_config.sh
            [ -f "$DEPLOY_DIR/.env.production" ] && print_success "配置生成完成" || print_error "配置生成可能失败，请检查"
        else
            print_error "缺少 scripts/generate_production_config.sh"
        fi
    else
        print_info "已跳过生成，如需生成：cd $DEPLOY_DIR && bash scripts/generate_production_config.sh"
    fi
else
    print_info ".env.production 已存在：$DEPLOY_DIR/.env.production（如需重建请删除后强制覆盖）"
fi

# 8. 校验与摘要
print_step "校验配置"
if grep -q "build:" "$DEPLOY_DIR/docker-compose.prod.yml" 2>/dev/null; then
    print_warning "docker-compose.prod.yml 含 build 段，如使用已导入镜像请改用 1Panel 版本或手动移除 build"
else
    print_success "Compose 校验通过（无 build）"
fi

if grep -q "root /usr/share/nginx/html" "$DEPLOY_DIR/nginx/nginx.conf" 2>/dev/null && \
   ! grep -q "upstream frontend_backend" "$DEPLOY_DIR/nginx/nginx.conf" 2>/dev/null; then
    print_success "Nginx 配置符合 Scheme B（单 Nginx）"
else
    print_warning "Nginx 配置可能不符合 Scheme B（期望 root /usr/share/nginx/html 且无 frontend upstream）"
fi

if grep -q "frontend/dist:/usr/share/nginx/html" "$DEPLOY_DIR/docker-compose.prod.yml" 2>/dev/null; then
    print_success "Compose 已挂载前端静态目录"
else
    print_warning "Compose 可能缺少前端静态目录挂载（期望 nginx 服务含 ./frontend/dist:/usr/share/nginx/html:ro）"
fi

if grep -A 5 "^  frontend:" "$DEPLOY_DIR/docker-compose.prod.yml" 2>/dev/null | grep -q 'restart: "no"'; then
    print_success "frontend 服务（如存在）restart: \"no\" 正确"
else
    print_info "前端服务配置检查跳过（可能已注释）"
fi

echo -e "\n${CYAN}=========================================================================${NC}"
echo -e "${GREEN}                 最小化部署包已就绪${NC}"
echo -e "${CYAN}=========================================================================${NC}\n"

print_step "部署内容摘要"
echo -e "${BLUE}部署目录:${NC} $DEPLOY_DIR\n"
echo -e "${GREEN}包含内容:${NC}"
echo "  ✓ docker-compose.prod.yml"
[ -f "$DEPLOY_DIR/.env.production" ] && env_size=$(stat -f%z "$DEPLOY_DIR/.env.production" 2>/dev/null || stat -c%s "$DEPLOY_DIR/.env.production") && echo "  ✓ .env.production（$env_size bytes）" || echo "  ⚠ .env.production 待生成"
[ -d "$DEPLOY_DIR/config" ] && cfg_cnt=$(find "$DEPLOY_DIR/config" -type f | wc -l) && echo "  ✓ config/（$cfg_cnt 个文件）"
[ -d "$DEPLOY_DIR/models" ] && mdl_cnt=$(find "$DEPLOY_DIR/models" -type f | wc -l) && echo "  ✓ models/（$mdl_cnt 个文件）"
[ -d "$DEPLOY_DIR/nginx" ] && echo "  ✓ nginx/ 配置目录"
if [ -d "$DEPLOY_DIR/frontend/dist" ]; then
    fe_cnt=$(find "$DEPLOY_DIR/frontend/dist" -type f 2>/dev/null | wc -l)
    if [ "$fe_cnt" -gt 0 ]; then
        echo "  ✓ frontend/dist/ 静态文件（$fe_cnt 个）"
    else
        echo "  ⚠ frontend/dist/ 为空，frontend-init 启动时会填充"
    fi
else
    echo "  ⚠ frontend/dist/ 未找到（Scheme B 需要）"
fi
echo "  ✓ scripts/（部署脚本已赋权）"

echo -e "\n${BLUE}后续操作:${NC}"
if [ ! -f "$DEPLOY_DIR/.env.production" ]; then
    echo "  1. 生成配置：cd $DEPLOY_DIR && bash scripts/generate_production_config.sh"
else
    echo "  1. 配置文件已就绪"
fi
echo "  2. 确认前端静态文件（可为空，frontend-init 会填充）"
echo "  3. 启动服务："
echo "     cd $DEPLOY_DIR"
echo "     docker-compose -f docker-compose.prod.yml --env-file .env.production up -d"
echo "  4. 校验：docker-compose -f docker-compose.prod.yml --env-file .env.production config"
echo "  5. 查看状态：docker-compose -f docker-compose.prod.yml ps"
echo "  6. 健康检查："
echo "     curl http://localhost/health"
echo "     curl http://localhost/"
echo "     curl http://localhost/api/v1/monitoring/health"

echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}架构：Scheme B（单 Nginx）${NC}"
echo "  • Nginx 直接服务 ./frontend/dist"
echo "  • 前端容器可选（用于构建静态文件）"
echo "  • frontend-init 启动时可自动解压静态文件"
echo ""
echo -e "${BLUE}提示:${NC}"
echo "  • 如使用已导入镜像，确保 .env.production 中 IMAGE_TAG 一致"
echo "  • 静态目录需存在，frontend-init 会写入；Nginx 配置以源码为准"
echo "  • docker-entrypoint.sh 负责迁移，已复制到部署目录"
echo "  • 再次运行本脚本会自动检测差异；强制覆盖：bash $0 $DEPLOY_DIR yes"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
