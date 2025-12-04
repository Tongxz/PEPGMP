#!/bin/bash
# Prepare minimal deployment package (only runtime required files)
# Support incremental update: detect file existence and differences, avoid unnecessary overwrites

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default deployment directory
DEPLOY_DIR="${1:-$HOME/projects/Pyt}"
# Force overwrite flag (default: no)
FORCE_OVERWRITE="${2:-no}"

echo "========================================================================="
echo "              Prepare Minimal Deployment Package"
echo "========================================================================="
echo ""
echo "Source directory: $PROJECT_ROOT"
echo "Target directory: $DEPLOY_DIR"
echo "Force overwrite: $FORCE_OVERWRITE"
echo ""

# Color definitions for better visualization
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Progress indicators
STEP=0
TOTAL_STEPS=8

print_step() {
    STEP=$((STEP + 1))
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}[Step $STEP/$TOTAL_STEPS]${NC} $1"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# File comparison function (跨平台兼容)
file_needs_update() {
    local src_file="$1"
    local dst_file="$2"

    # If destination file doesn't exist, need to copy
    if [ ! -f "$dst_file" ]; then
        return 0  # Need update
    fi

    # If force overwrite, need to copy
    if [ "$FORCE_OVERWRITE" = "yes" ] || [ "$FORCE_OVERWRITE" = "y" ]; then
        return 0  # Need update
    fi

    # Compare file content using available tools
    # Priority: md5/md5sum > shasum > diff > size comparison

    # macOS uses md5, Linux uses md5sum
    if command -v md5sum >/dev/null 2>&1; then
        src_hash=$(md5sum "$src_file" 2>/dev/null | cut -d' ' -f1)
        dst_hash=$(md5sum "$dst_file" 2>/dev/null | cut -d' ' -f1)
        if [ -n "$src_hash" ] && [ -n "$dst_hash" ] && [ "$src_hash" != "$dst_hash" ]; then
            return 0  # Need update
        elif [ -n "$src_hash" ] && [ -n "$dst_hash" ]; then
            return 1  # No update needed
        fi
    elif command -v md5 >/dev/null 2>&1; then
        # macOS md5 command
        src_hash=$(md5 -q "$src_file" 2>/dev/null)
        dst_hash=$(md5 -q "$dst_file" 2>/dev/null)
        if [ -n "$src_hash" ] && [ -n "$dst_hash" ] && [ "$src_hash" != "$dst_hash" ]; then
            return 0  # Need update
        elif [ -n "$src_hash" ] && [ -n "$dst_hash" ]; then
            return 1  # No update needed
        fi
    elif command -v shasum >/dev/null 2>&1; then
        src_hash=$(shasum "$src_file" 2>/dev/null | cut -d' ' -f1)
        dst_hash=$(shasum "$dst_file" 2>/dev/null | cut -d' ' -f1)
        if [ -n "$src_hash" ] && [ -n "$dst_hash" ] && [ "$src_hash" != "$dst_hash" ]; then
            return 0  # Need update
        elif [ -n "$src_hash" ] && [ -n "$dst_hash" ]; then
            return 1  # No update needed
        fi
    fi

    # Fallback to diff
    if command -v diff >/dev/null 2>&1; then
        if ! diff -q "$src_file" "$dst_file" >/dev/null 2>&1; then
            return 0  # Need update
        fi
        return 1  # No update needed
    fi

    # Last resort: compare file size (跨平台兼容)
    local src_size dst_size
    if [ "$(uname)" = "Darwin" ]; then
        src_size=$(stat -f%z "$src_file" 2>/dev/null)
        dst_size=$(stat -f%z "$dst_file" 2>/dev/null)
    else
        src_size=$(stat -c%s "$src_file" 2>/dev/null)
        dst_size=$(stat -c%s "$dst_file" 2>/dev/null)
    fi

    if [ "$src_size" != "$dst_size" ]; then
        return 0  # Need update
    fi

    return 1  # No update needed (assume same if size matches)
}

# Copy file function (with check)
safe_copy_file() {
    local src_file="$1"
    local dst_file="$2"
    local description="${3:-file}"

    if [ ! -f "$src_file" ]; then
        echo "WARNING: Source file does not exist: $src_file"
        return 1
    fi

    if file_needs_update "$src_file" "$dst_file"; then
        mkdir -p "$(dirname "$dst_file")"
        cp "$src_file" "$dst_file"
        print_success "Updated: ${description}"
        return 0
    else
        print_info "Skipped: ${description} (file exists and identical)"
        return 0
    fi
}

# Copy directory function (with check)
# 改进版本：使用 rsync（如果可用）或详细比较
safe_copy_dir() {
    local src_dir="$1"
    local dst_dir="$2"
    local description="${3:-directory}"

    if [ ! -d "$src_dir" ]; then
        echo "WARNING: Source directory does not exist: $src_dir"
        return 1
    fi

    # Check if directory is empty
    if [ -z "$(ls -A "$src_dir" 2>/dev/null)" ]; then
        echo "INFO: Source directory is empty: $src_dir"
        mkdir -p "$dst_dir"
        return 0
    fi

    # If destination doesn't exist or force overwrite, copy directly
    if [ ! -d "$dst_dir" ] || [ "$FORCE_OVERWRITE" = "yes" ] || [ "$FORCE_OVERWRITE" = "y" ]; then
        mkdir -p "$(dirname "$dst_dir")"
        cp -r "$src_dir" "$(dirname "$dst_dir")/"
        print_success "Updated: ${description}"
        return 0
    fi

    # 优先使用 rsync 进行增量同步（如果可用）
    if command -v rsync >/dev/null 2>&1; then
        # rsync 会自动检测并只复制变化的文件
        local changes
        changes=$(rsync -avnc --delete "$src_dir/" "$dst_dir/" 2>/dev/null | grep -c "^[^>]" || echo "0")
        if [ "$changes" -gt 2 ]; then  # rsync 输出至少有 2 行标题
            rsync -av --delete "$src_dir/" "$dst_dir/" >/dev/null 2>&1
            print_success "Updated: ${description} (incremental sync with rsync)"
            return 0
        else
            print_info "Skipped: ${description} (no changes detected by rsync)"
            return 0
        fi
    fi

    # 备选方案：比较文件数量和总大小
    src_count=$(find "$src_dir" -type f | wc -l | tr -d ' ')
    dst_count=$(find "$dst_dir" -type f 2>/dev/null | wc -l | tr -d ' ')

    # 获取目录大小（跨平台兼容）
    if [ "$(uname)" = "Darwin" ]; then
        src_size=$(du -sk "$src_dir" 2>/dev/null | cut -f1)
        dst_size=$(du -sk "$dst_dir" 2>/dev/null | cut -f1)
    else
        src_size=$(du -s "$src_dir" 2>/dev/null | cut -f1)
        dst_size=$(du -s "$dst_dir" 2>/dev/null | cut -f1)
    fi

    if [ "$src_count" -ne "$dst_count" ] || [ "$src_size" -ne "$dst_size" ]; then
        mkdir -p "$(dirname "$dst_dir")"
        rm -rf "$dst_dir"
        cp -r "$src_dir" "$(dirname "$dst_dir")/"
        print_success "Updated: ${description} (files: ${src_count} vs ${dst_count}, size: ${src_size}KB vs ${dst_size}KB)"
        return 0
    else
        print_info "Skipped: ${description} (files: ${src_count}, size: ${src_size}KB - no changes)"
        return 0
    fi
}

# Create directories
print_step "Creating directory structure"
print_info "Creating required directories in: $DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"/{config,models,data,logs,scripts,nginx/ssl}
print_success "Directory structure created"

# Copy Docker Compose file (use 1Panel version if available)
print_step "Copying Docker Compose configuration file"

if [ -f "$PROJECT_ROOT/docker-compose.prod.1panel.yml" ]; then
    print_info "Found docker-compose.prod.1panel.yml (1Panel version)"
    print_info "Using 1Panel version (no build section, uses pre-imported images)"
    safe_copy_file \
        "$PROJECT_ROOT/docker-compose.prod.1panel.yml" \
        "$DEPLOY_DIR/docker-compose.prod.yml" \
        "docker-compose.prod.yml (1Panel version)"
else
    print_warning "docker-compose.prod.1panel.yml not found, using standard version"
    print_info "Note: Standard version may contain build section"
    safe_copy_file \
        "$PROJECT_ROOT/docker-compose.prod.yml" \
        "$DEPLOY_DIR/docker-compose.prod.yml" \
        "docker-compose.prod.yml (need to manually remove build section)"
fi

# Copy configuration directory
print_step "Copying configuration files"
print_info "Copying config/ directory..."
safe_copy_dir \
    "$PROJECT_ROOT/config" \
    "$DEPLOY_DIR/config" \
    "config/ (configuration directory)"

# Copy model files directory (if exists)
# 智能模型复制策略：
# 1. 首次部署：如果目标目录不存在，复制所有模型
# 2. 后续部署：检测新增模型，询问用户是否复制
# 3. 已存在的模型：跳过（除非强制覆盖）
print_step "Copying models/ directory"
if [ -d "$PROJECT_ROOT/models" ] && [ -n "$(ls -A "$PROJECT_ROOT/models" 2>/dev/null)" ]; then
    MODEL_COUNT=$(find "$PROJECT_ROOT/models" -type f | wc -l | tr -d ' ')
    print_info "Found $MODEL_COUNT model files"

    # 计算总大小（用于显示）
    if [ "$(uname)" = "Darwin" ]; then
        TOTAL_SIZE=$(du -sh "$PROJECT_ROOT/models" 2>/dev/null | cut -f1)
    else
        TOTAL_SIZE=$(du -sh "$PROJECT_ROOT/models" 2>/dev/null | cut -f1)
    fi
    print_info "Total size: $TOTAL_SIZE"

    # 首次部署：目标目录不存在或强制覆盖
    if [ ! -d "$DEPLOY_DIR/models" ] || [ "$FORCE_OVERWRITE" = "yes" ] || [ "$FORCE_OVERWRITE" = "y" ]; then
        if [ ! -d "$DEPLOY_DIR/models" ]; then
            print_info "首次部署：复制所有模型文件..."
        else
            print_info "强制覆盖：复制所有模型文件..."
        fi
        mkdir -p "$(dirname "$DEPLOY_DIR/models")"

        # 使用 rsync 带进度显示（如果可用）
        if command -v rsync >/dev/null 2>&1; then
            print_info "Using rsync with progress (this may take a while for large directories)..."
            rsync -av --info=progress2 "$PROJECT_ROOT/models/" "$DEPLOY_DIR/models/" 2>&1 | \
                while IFS= read -r line; do
                    if echo "$line" | grep -qE "(to-check|to-chk|^[0-9])"; then
                        echo -ne "\r${BLUE}[INFO]${NC} $line"
                    fi
                done
            echo ""  # 换行
            print_success "Copied models/ directory ($MODEL_COUNT files, $TOTAL_SIZE)"
        else
            print_info "Using cp (rsync not available, this may take a while)..."
            print_info "Progress: Copying $MODEL_COUNT files..."
            cp -r "$PROJECT_ROOT/models" "$(dirname "$DEPLOY_DIR/models")/"
            print_success "Copied models/ directory ($MODEL_COUNT files, $TOTAL_SIZE)"
        fi
    else
        # 后续部署：检测新增模型
        print_info "检测新增模型文件..."

        # 查找新增的模型文件（在源目录存在但目标目录不存在）
        NEW_MODELS=()
        while IFS= read -r -d '' file; do
            # 获取相对路径
            rel_path="${file#$PROJECT_ROOT/models/}"
            dst_file="$DEPLOY_DIR/models/$rel_path"

            # 如果目标文件不存在，则认为是新增的
            if [ ! -f "$dst_file" ]; then
                NEW_MODELS+=("$rel_path")
            fi
        done < <(find "$PROJECT_ROOT/models" -type f -print0 2>/dev/null)

        if [ ${#NEW_MODELS[@]} -gt 0 ]; then
            echo ""
            print_warning "发现 ${#NEW_MODELS[@]} 个新增模型文件:"
            echo ""
            for model in "${NEW_MODELS[@]}"; do
                # 显示文件大小
                if [ "$(uname)" = "Darwin" ]; then
                    FILE_SIZE=$(stat -f%z "$PROJECT_ROOT/models/$model" 2>/dev/null || echo "0")
                else
                    FILE_SIZE=$(stat -c%s "$PROJECT_ROOT/models/$model" 2>/dev/null || echo "0")
                fi

                # 转换为人类可读格式
                if [ "$FILE_SIZE" -gt 1048576 ]; then
                    SIZE_STR=$(echo "scale=2; $FILE_SIZE / 1048576" | bc)MB
                elif [ "$FILE_SIZE" -gt 1024 ]; then
                    SIZE_STR=$(echo "scale=2; $FILE_SIZE / 1024" | bc)KB
                else
                    SIZE_STR="${FILE_SIZE}B"
                fi

                echo "  - $model ($SIZE_STR)"
            done
            echo ""

            # 询问用户是否复制
            read -p "是否复制这些新增模型文件到部署目录? (y/N): " -n 1 -r
            echo ""

            if [[ $REPLY =~ ^[Yy]$ ]]; then
                print_info "复制新增模型文件..."

                # 复制新增文件
                for model in "${NEW_MODELS[@]}"; do
                    src_file="$PROJECT_ROOT/models/$model"
                    dst_file="$DEPLOY_DIR/models/$model"
                    mkdir -p "$(dirname "$dst_file")"
                    cp "$src_file" "$dst_file"
                    print_success "已复制: $model"
                done

                echo ""
                print_success "新增模型文件复制完成"
            else
                print_info "跳过新增模型文件复制"
            fi
        else
            print_info "未发现新增模型文件，跳过复制"
        fi

        # 检查是否有文件变化（已存在的文件）
        if command -v rsync >/dev/null 2>&1; then
            print_info "检查已存在文件的变化..."
            CHANGES=$(rsync -avnc --delete "$PROJECT_ROOT/models/" "$DEPLOY_DIR/models/" 2>/dev/null | grep -c "^[^>]" || echo "0")

            if [ "$CHANGES" -gt 2 ]; then
                print_warning "发现已存在文件有变化（${CHANGES} 个文件）"
                print_info "注意: 已存在的模型文件不会被自动更新，如需更新请使用 --force 参数"
            fi
        fi
    fi
else
    print_warning "models/ directory does not exist or is empty"
    print_info "Creating empty models/ directory"
    mkdir -p "$DEPLOY_DIR/models"
fi

# Prepare nginx configuration
print_step "Preparing Nginx configuration"

# 重要：配置的唯一真理来源是源码中的 nginx/nginx.conf
# 脚本只负责复制，不进行硬编码生成，避免配置漂移
print_info "Using nginx.conf from source code (single source of truth)"

# 检查源码中是否存在 nginx.conf
if [ ! -f "$PROJECT_ROOT/nginx/nginx.conf" ]; then
    print_error "nginx/nginx.conf not found in source code!"
    print_error "  Expected location: $PROJECT_ROOT/nginx/nginx.conf"
    print_error "  This file must exist in the source code repository."
    print_error "  Please ensure nginx/nginx.conf is committed to the repository."
    exit 1
fi

print_success "Found nginx.conf in source code: $PROJECT_ROOT/nginx/nginx.conf"

# 确保 nginx 目录结构存在
print_info "Ensuring nginx directory structure exists..."
mkdir -p "$PROJECT_ROOT/nginx/ssl"
print_success "nginx directory structure ready"

# 注意：不再硬编码生成 nginx.conf，而是直接复制源码中的配置文件
# 这样可以确保配置的唯一真理来源，避免脚本和源码配置不一致
# Nginx 配置文件将在后续步骤中从源码复制到部署目录

# Prepare frontend static files directory (Scheme B requirement)
print_step "Preparing frontend static files directory (Scheme B)"

FRONTEND_DIST_TARGET="$DEPLOY_DIR/frontend/dist"

# 在 Scheme B 架构中，frontend-init 容器会在启动时自动提取静态文件
# 脚本的核心任务：确保目录存在（防止 Docker 挂载报错）
# 可选：如果源码中有静态文件，可以复制作为加速手段（但非必需）

print_info "Scheme B: frontend-init container will extract static files on startup"
print_info "  Script task: Ensure directory exists for Docker volume mount"

# 确保目录存在
mkdir -p "$FRONTEND_DIST_TARGET"
print_success "Frontend dist directory created: $FRONTEND_DIST_TARGET"

# 可选：如果源码中有静态文件，复制作为加速手段（但非必需）
if [ -d "$PROJECT_ROOT/frontend/dist" ] && [ -f "$PROJECT_ROOT/frontend/dist/index.html" ]; then
    print_info "Found frontend static files in source code (optional pre-population)"
    print_info "  → Copying to deployment directory as optimization (frontend-init will overwrite if newer)"

    SOURCE_FILE_COUNT=$(find "$PROJECT_ROOT/frontend/dist" -type f | wc -l)

    if [ "$FORCE_OVERWRITE" = "yes" ] || [ "$FORCE_OVERWRITE" = "y" ] || [ ! -f "$FRONTEND_DIST_TARGET/index.html" ]; then
        print_info "  → Copying $SOURCE_FILE_COUNT files..."
        cp -r "$PROJECT_ROOT/frontend/dist"/* "$FRONTEND_DIST_TARGET/" 2>/dev/null || {
            print_warning "Failed to copy frontend static files (non-fatal, frontend-init will handle)"
        }
        print_success "Frontend static files pre-populated (frontend-init will update on startup)"
    else
        print_info "  → Static files already exist, skipping pre-population"
        print_info "  → frontend-init container will update files on startup if needed"
    fi
else
    print_info "No frontend static files in source code (this is OK)"
    print_info "  → frontend-init container will extract files from image on first startup"
    print_info "  → Directory is ready for Docker volume mount"
fi

# 验证目录存在
if [ -d "$FRONTEND_DIST_TARGET" ]; then
    print_success "Frontend dist directory ready: $FRONTEND_DIST_TARGET"
    if [ -f "$FRONTEND_DIST_TARGET/index.html" ]; then
        FILE_COUNT=$(find "$FRONTEND_DIST_TARGET" -type f 2>/dev/null | wc -l)
        print_info "  → Pre-populated with $FILE_COUNT files (frontend-init will update if needed)"
    else
        print_info "  → Directory is empty (frontend-init will populate on startup)"
    fi
else
    print_error "Failed to create frontend dist directory"
    exit 1
fi

# Copy nginx directory to deployment directory
print_info "Copying nginx configuration to deployment directory..."

# Clean up any incorrect directory structure in deploy dir
if [ -d "$DEPLOY_DIR/nginx/nginx.conf" ]; then
    print_warning "Found incorrect directory structure at nginx/nginx.conf"
    print_info "  → Removing incorrect directory..."
    sudo rm -rf "$DEPLOY_DIR/nginx/nginx.conf" 2>/dev/null || rm -rf "$DEPLOY_DIR/nginx/nginx.conf"
    print_success "Incorrect directory structure removed"
fi

# Fix permissions in deploy dir before copying
if [ -d "$DEPLOY_DIR/nginx" ]; then
    CURRENT_USER=$(whoami)
    print_info "Fixing permissions for existing nginx directory..."
    sudo chown -R "$CURRENT_USER:$CURRENT_USER" "$DEPLOY_DIR/nginx/" 2>/dev/null || chown -R "$CURRENT_USER:$CURRENT_USER" "$DEPLOY_DIR/nginx/" 2>/dev/null || true
    print_success "Permissions fixed"
fi

# Copy nginx directory
print_info "  → Copying nginx configuration files..."
safe_copy_dir \
    "$PROJECT_ROOT/nginx" \
    "$DEPLOY_DIR/nginx" \
    "nginx/ (nginx configuration directory)"

# Ensure correct permissions after copying
if [ -f "$DEPLOY_DIR/nginx/nginx.conf" ]; then
    print_info "  → Setting correct file permissions..."
    chmod 644 "$DEPLOY_DIR/nginx/nginx.conf"
    CURRENT_USER=$(whoami)
    chown "$CURRENT_USER:$CURRENT_USER" "$DEPLOY_DIR/nginx/nginx.conf" 2>/dev/null || true
    print_success "nginx.conf permissions set correctly in deployment directory"
    print_info "  → File: $DEPLOY_DIR/nginx/nginx.conf"
else
    print_error "nginx.conf was not copied successfully"
fi

# Copy configuration generation script
print_step "Copying deployment scripts"

# 复制生产配置生成脚本
print_info "Copying generate_production_config.sh..."
safe_copy_file \
    "$PROJECT_ROOT/scripts/generate_production_config.sh" \
    "$DEPLOY_DIR/scripts/generate_production_config.sh" \
    "scripts/generate_production_config.sh"

# 复制数据库初始化脚本（Docker Compose 需要挂载此文件）
print_info "Copying init_db.sql..."
safe_copy_file \
    "$PROJECT_ROOT/scripts/init_db.sql" \
    "$DEPLOY_DIR/scripts/init_db.sql" \
    "scripts/init_db.sql"

# 复制 Docker Entrypoint 脚本（API 容器启动需要）
print_info "Copying docker-entrypoint.sh..."
if [ ! -f "$PROJECT_ROOT/scripts/docker-entrypoint.sh" ]; then
    print_error "docker-entrypoint.sh not found in source code!"
    print_error "  Expected location: $PROJECT_ROOT/scripts/docker-entrypoint.sh"
    print_error "  This file is required for API container startup (database migration)."
    exit 1
fi
safe_copy_file \
    "$PROJECT_ROOT/scripts/docker-entrypoint.sh" \
    "$DEPLOY_DIR/scripts/docker-entrypoint.sh" \
    "scripts/docker-entrypoint.sh"

# 复制镜像导入脚本（WSL/Linux 部署需要）
print_info "Copying import_images_from_windows.sh..."
safe_copy_file \
    "$PROJECT_ROOT/scripts/import_images_from_windows.sh" \
    "$DEPLOY_DIR/scripts/import_images_from_windows.sh" \
    "scripts/import_images_from_windows.sh"

# 复制版本更新脚本
print_info "Copying update_image_version.sh..."
safe_copy_file \
    "$PROJECT_ROOT/scripts/update_image_version.sh" \
    "$DEPLOY_DIR/scripts/update_image_version.sh" \
    "scripts/update_image_version.sh"

# Set script execution permissions
print_info "Setting script execution permissions..."
for script in "$DEPLOY_DIR/scripts/"*.sh; do
    if [ -f "$script" ]; then
        chmod +x "$script"
    fi
done
print_success "Script execution permissions set"

# Handle environment variable file
print_step "Handling environment configuration file"

if [ ! -f "$DEPLOY_DIR/.env.production" ]; then
    print_warning ".env.production does not exist, needs generation"
    echo ""
    print_info "The configuration generation script will:"
    echo "  ✓ Generate complete .env.production file"
    echo "  ✓ Automatically generate strong random passwords"
    echo "  ✓ Create .env.production.credentials file"
    echo "  ✓ Set correct file permissions"
    echo ""
    read -p "$(echo -e ${YELLOW}Run configuration generation script now? [y/n] [y]: ${NC})" run_generate
    run_generate=${run_generate:-y}

    if [ "$run_generate" = "y" ] || [ "$run_generate" = "Y" ]; then
        print_info "Running configuration generation script..."
        cd "$DEPLOY_DIR"
        if [ -f "scripts/generate_production_config.sh" ]; then
            bash scripts/generate_production_config.sh
            echo ""
            if [ -f "$DEPLOY_DIR/.env.production" ]; then
                print_success "Configuration file generated successfully"
            else
                print_error "Configuration file generation may have failed"
            fi
        else
            print_error "Configuration generation script does not exist"
        fi
    else
        echo ""
        print_warning "Skipping configuration generation"
        print_info "To generate later, run: cd $DEPLOY_DIR && bash scripts/generate_production_config.sh"
    fi
else
    print_info ".env.production already exists"
    print_info "  → File: $DEPLOY_DIR/.env.production"
    print_info "  → To regenerate, delete it and re-run this script with force overwrite"
fi

# Check if docker-compose.prod.yml contains build section
print_step "Validating Docker Compose configuration"

if grep -q "build:" "$DEPLOY_DIR/docker-compose.prod.yml" 2>/dev/null; then
    print_warning "docker-compose.prod.yml contains build section"
    print_info "  → If using imported images, ensure using docker-compose.prod.1panel.yml"
    print_info "  → Or manually remove build section from docker-compose.prod.yml"
else
    print_success "Docker Compose configuration validated (no build section)"
fi

# Validate Scheme B architecture requirements
print_info "Validating Scheme B (Single Nginx) architecture requirements..."

# Check if nginx.conf has correct Scheme B configuration
if grep -q "root /usr/share/nginx/html" "$DEPLOY_DIR/nginx/nginx.conf" 2>/dev/null && \
   ! grep -q "upstream frontend_backend" "$DEPLOY_DIR/nginx/nginx.conf" 2>/dev/null; then
    print_success "Nginx configuration matches Scheme B (Single Nginx)"
else
    print_warning "Nginx configuration may not match Scheme B architecture"
    print_info "  → Expected: root /usr/share/nginx/html (no frontend upstream)"
fi

# Check if docker-compose has frontend volume mount
if grep -q "frontend/dist:/usr/share/nginx/html" "$DEPLOY_DIR/docker-compose.prod.yml" 2>/dev/null; then
    print_success "Docker Compose has frontend static files volume mount"
else
    print_warning "Docker Compose may be missing frontend static files volume mount"
    print_info "  → Expected: ./frontend/dist:/usr/share/nginx/html:ro in nginx service"
fi

# Check if frontend service has restart: "no"
if grep -A 5 "^  frontend:" "$DEPLOY_DIR/docker-compose.prod.yml" 2>/dev/null | grep -q 'restart: "no"'; then
    print_success "Frontend service configured correctly (restart: no)"
else
    print_info "Frontend service configuration check skipped (service may be commented out)"
fi

# Summary
echo ""
echo -e "${CYAN}=========================================================================${NC}"
echo -e "${GREEN}              Minimal Deployment Package Ready${NC}"
echo -e "${CYAN}=========================================================================${NC}"
echo ""

print_step "Deployment Summary"

echo -e "${BLUE}Deployment directory:${NC} $DEPLOY_DIR"
echo ""

echo -e "${GREEN}Files included:${NC}"
echo "  ✓ docker-compose.prod.yml"

if [ -f "$DEPLOY_DIR/.env.production" ]; then
    echo -e "  ${GREEN}✓${NC} .env.production (exists)"
    ENV_SIZE=$(stat -f%z "$DEPLOY_DIR/.env.production" 2>/dev/null || stat -c%s "$DEPLOY_DIR/.env.production" 2>/dev/null)
    echo "    → Size: $ENV_SIZE bytes"
else
    echo -e "  ${YELLOW}⚠${NC}  .env.production (needs generation)"
fi

if [ -d "$DEPLOY_DIR/config" ]; then
    CONFIG_COUNT=$(find "$DEPLOY_DIR/config" -type f 2>/dev/null | wc -l)
    echo "  ✓ config/ (configuration directory) - $CONFIG_COUNT files"
fi

if [ -d "$DEPLOY_DIR/models" ]; then
    MODEL_COUNT=$(find "$DEPLOY_DIR/models" -type f 2>/dev/null | wc -l)
    echo "  ✓ models/ (model files directory) - $MODEL_COUNT files"
fi

if [ -d "$DEPLOY_DIR/nginx" ]; then
    echo "  ✓ nginx/ (nginx configuration directory)"
    if [ -f "$DEPLOY_DIR/nginx/nginx.conf" ]; then
        NGINX_SIZE=$(stat -f%z "$DEPLOY_DIR/nginx/nginx.conf" 2>/dev/null || stat -c%s "$DEPLOY_DIR/nginx/nginx.conf" 2>/dev/null)
        echo "    → nginx.conf: $NGINX_SIZE bytes"
    fi
fi

if [ -d "$DEPLOY_DIR/frontend/dist" ]; then
    FRONTEND_FILE_COUNT=$(find "$DEPLOY_DIR/frontend/dist" -type f 2>/dev/null | wc -l)
    if [ "$FRONTEND_FILE_COUNT" -gt 0 ]; then
        echo -e "  ${GREEN}✓${NC} frontend/dist/ (frontend static files) - $FRONTEND_FILE_COUNT files"
        if [ -f "$DEPLOY_DIR/frontend/dist/index.html" ]; then
            echo "    → index.html exists"
        else
            echo -e "    ${YELLOW}⚠${NC}  index.html missing"
        fi
    else
        echo -e "  ${YELLOW}⚠${NC}  frontend/dist/ (empty or missing)"
    fi
else
    echo -e "  ${YELLOW}⚠${NC}  frontend/dist/ (not found - required for Scheme B)"
fi

echo "  ✓ scripts/ (scripts directory)"
echo ""

echo -e "${BLUE}Next steps:${NC}"
if [ ! -f "$DEPLOY_DIR/.env.production" ]; then
    echo -e "  ${YELLOW}1.${NC} Run configuration generation script:"
    echo "     cd $DEPLOY_DIR"
    echo "     bash scripts/generate_production_config.sh"
    echo ""
    echo -e "  ${BLUE}2.${NC} Verify frontend static files (Scheme B requirement):"
else
    echo -e "  ${GREEN}1.${NC} ✓ Configuration file ready"
    echo ""
    echo -e "  ${BLUE}2.${NC} Verify frontend static files (Scheme B requirement):"
fi

if [ -d "$DEPLOY_DIR/frontend/dist" ] && [ -f "$DEPLOY_DIR/frontend/dist/index.html" ]; then
    echo -e "     ${GREEN}✓${NC} Frontend static files ready (pre-populated)"
    echo "     → frontend-init container will update on startup if needed"
else
    echo -e "     ${YELLOW}⚠${NC}  Frontend static files directory is empty"
    echo "     → This is OK - frontend-init container will extract files on first startup"
    echo "     → Directory exists: $DEPLOY_DIR/frontend/dist"
fi
echo ""
echo -e "  ${BLUE}3.${NC} Start services:"
echo "     cd $DEPLOY_DIR"
echo "     docker-compose -f docker-compose.prod.yml --env-file .env.production up -d"
echo ""
echo -e "  ${BLUE}4.${NC} Verify configuration:"
echo "     docker-compose -f docker-compose.prod.yml --env-file .env.production config"
echo ""
echo -e "  ${BLUE}5.${NC} Check service status:"
echo "     docker-compose -f docker-compose.prod.yml ps"
echo ""
echo -e "  ${BLUE}6.${NC} Test deployment (Scheme B):"
echo "     curl http://localhost/health          # Nginx health check"
echo "     curl http://localhost/                # Frontend static files"
echo "     curl http://localhost/api/v1/monitoring/health  # API proxy"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Architecture: Scheme B (Single Nginx)${NC}"
echo "  • Nginx serves static files directly from ./frontend/dist"
echo "  • Frontend container is optional (only for building static files)"
echo "  • Static files must be built before deployment"
echo ""
echo -e "${BLUE}Tips:${NC}"
echo "  • If using imported images, ensure IMAGE_TAG in .env.production matches"
echo "  • Frontend static files: frontend-init container will extract on startup (directory must exist)"
echo "  • Nginx config: Copied from source code (nginx/nginx.conf) - single source of truth"
echo "  • Docker entrypoint: Copied from source code (scripts/docker-entrypoint.sh) - required for migrations"
echo "  • Credentials saved in .env.production.credentials (if generated)"
echo "  • Re-run this script automatically detects file differences"
echo "  • Force overwrite all files: bash $0 $DEPLOY_DIR yes"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
