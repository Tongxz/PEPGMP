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

# File comparison function
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
    
    # Compare file content (using md5sum or diff)
    if command -v md5sum >/dev/null 2>&1; then
        src_hash=$(md5sum "$src_file" | cut -d' ' -f1)
        dst_hash=$(md5sum "$dst_file" | cut -d' ' -f1)
        if [ "$src_hash" != "$dst_hash" ]; then
            return 0  # Need update
        fi
    elif command -v diff >/dev/null 2>&1; then
        if ! diff -q "$src_file" "$dst_file" >/dev/null 2>&1; then
            return 0  # Need update
        fi
    else
        # If no comparison tool, compare file size and modification time
        if [ "$(stat -f%z "$src_file" 2>/dev/null || stat -c%s "$src_file" 2>/dev/null)" != "$(stat -f%z "$dst_file" 2>/dev/null || stat -c%s "$dst_file" 2>/dev/null)" ]; then
            return 0  # Need update
        fi
    fi
    
    return 1  # No update needed
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
    
    # Compare directory content (simple check: compare file count)
    src_count=$(find "$src_dir" -type f | wc -l)
    dst_count=$(find "$dst_dir" -type f 2>/dev/null | wc -l)
    
    if [ "$src_count" -ne "$dst_count" ]; then
        mkdir -p "$(dirname "$dst_dir")"
        cp -r "$src_dir" "$(dirname "$dst_dir")/"
        print_success "Updated: ${description} (file count differs: ${src_count} vs ${dst_count})"
        return 0
    else
        print_info "Skipped: ${description} (file count same: ${src_count})"
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
print_info "Copying models/ directory..."
if [ -d "$PROJECT_ROOT/models" ] && [ -n "$(ls -A "$PROJECT_ROOT/models" 2>/dev/null)" ]; then
    MODEL_COUNT=$(find "$PROJECT_ROOT/models" -type f | wc -l)
    print_info "Found $MODEL_COUNT model files"
    safe_copy_dir \
        "$PROJECT_ROOT/models" \
        "$DEPLOY_DIR/models" \
        "models/ (model files directory)"
else
    print_warning "models/ directory does not exist or is empty"
    print_info "Creating empty models/ directory"
    mkdir -p "$DEPLOY_DIR/models"
fi

# Prepare nginx configuration
print_step "Preparing Nginx configuration"

# Ensure nginx directory exists in project root
print_info "Ensuring nginx directory exists in project root..."
mkdir -p "$PROJECT_ROOT/nginx/ssl"
print_success "nginx directory structure ready"

# Check if frontend image exists (in WSL2 or current system)
print_info "Checking for frontend Docker image..."
FRONTEND_IMAGE_EXISTS=0
if command -v docker >/dev/null 2>&1; then
    FRONTEND_IMAGE_EXISTS=$(docker images 2>/dev/null | grep -c pepgmp-frontend || echo "0")
    FRONTEND_IMAGE_EXISTS=$(echo "$FRONTEND_IMAGE_EXISTS" | tr -d '\n' | head -1)
    FRONTEND_IMAGE_EXISTS=${FRONTEND_IMAGE_EXISTS:-0}
    
    if [ "${FRONTEND_IMAGE_EXISTS:-0}" -gt 0 ]; then
        print_success "Frontend image detected (pepgmp-frontend)"
        print_info "Nginx will be configured with frontend support"
    else
        print_info "No frontend image found"
        print_info "Nginx will be configured for API only"
    fi
else
    print_warning "Docker command not available, cannot check for frontend image"
    print_info "Nginx will be configured for API only"
fi

# Create or update nginx.conf in project root
if [ ! -f "$PROJECT_ROOT/nginx/nginx.conf" ] || [ "$FORCE_OVERWRITE" = "yes" ] || [ "$FORCE_OVERWRITE" = "y" ]; then
    if [ -f "$PROJECT_ROOT/nginx/nginx.conf" ]; then
        print_info "Updating existing nginx.conf in project root (force overwrite)"
    else
        print_info "Creating nginx.conf in project root"
    fi
    
    if [ "${FRONTEND_IMAGE_EXISTS:-0}" -gt 0 ]; then
        print_info "  → Creating nginx config with frontend support..."
        cat > "$PROJECT_ROOT/nginx/nginx.conf" << 'NGINX_EOF'
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    sendfile on;
    keepalive_timeout 65;
    client_max_body_size 100M;

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss
               application/rss+xml font/truetype font/opentype
               application/vnd.ms-fontobject image/svg+xml;

    upstream api_backend {
        server api:8000;
    }

    upstream frontend_backend {
        server frontend:80;
    }

    server {
        listen 80;
        server_name _;

        location /api/ {
            proxy_pass http://api_backend/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        location /api/v1/monitoring/health {
            proxy_pass http://api_backend/api/v1/monitoring/health;
            access_log off;
        }

        location / {
            proxy_pass http://frontend_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
NGINX_EOF
    else
        print_info "  → Creating nginx config for API only..."
        cat > "$PROJECT_ROOT/nginx/nginx.conf" << 'NGINX_EOF'
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    sendfile on;
    keepalive_timeout 65;
    client_max_body_size 100M;

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss
               application/rss+xml font/truetype font/opentype
               application/vnd.ms-fontobject image/svg+xml;

    upstream api_backend {
        server api:8000;
    }

    server {
        listen 80;
        server_name _;

        location /api/ {
            proxy_pass http://api_backend/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        location /api/v1/monitoring/health {
            proxy_pass http://api_backend/api/v1/monitoring/health;
            access_log off;
        }

        location / {
            proxy_pass http://api_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
NGINX_EOF
    fi
    
    chmod 644 "$PROJECT_ROOT/nginx/nginx.conf"
    print_success "nginx.conf created/updated in project root: $PROJECT_ROOT/nginx/nginx.conf"
else
    print_info "nginx.conf already exists in project root"
    print_info "  → Using existing: $PROJECT_ROOT/nginx/nginx.conf"
    print_info "  → To regenerate, use force overwrite: bash $0 $DEPLOY_DIR yes"
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
print_info "Copying generate_production_config.sh..."
safe_copy_file \
    "$PROJECT_ROOT/scripts/generate_production_config.sh" \
    "$DEPLOY_DIR/scripts/generate_production_config.sh" \
    "scripts/generate_production_config.sh"

# Set script execution permissions
if [ -f "$DEPLOY_DIR/scripts/generate_production_config.sh" ]; then
    chmod +x "$DEPLOY_DIR/scripts/generate_production_config.sh"
    print_success "Script execution permissions set"
fi

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

echo "  ✓ scripts/ (scripts directory)"
echo ""

echo -e "${BLUE}Next steps:${NC}"
if [ ! -f "$DEPLOY_DIR/.env.production" ]; then
    echo -e "  ${YELLOW}1.${NC} Run configuration generation script:"
    echo "     cd $DEPLOY_DIR"
    echo "     bash scripts/generate_production_config.sh"
    echo ""
    echo -e "  ${BLUE}2.${NC} Start services:"
else
    echo -e "  ${GREEN}1.${NC} ✓ Configuration file ready"
    echo ""
    echo -e "  ${BLUE}2.${NC} Start services:"
fi

echo "     cd $DEPLOY_DIR"
echo "     docker-compose -f docker-compose.prod.yml --env-file .env.production up -d"
echo ""
echo -e "  ${BLUE}3.${NC} Verify configuration:"
echo "     docker-compose -f docker-compose.prod.yml --env-file .env.production config"
echo ""
echo -e "  ${BLUE}4.${NC} Check service status:"
echo "     docker-compose -f docker-compose.prod.yml ps"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Tips:${NC}"
echo "  • If using imported images, ensure IMAGE_TAG in .env.production matches"
echo "  • Credentials saved in .env.production.credentials (if generated)"
echo "  • Re-run this script automatically detects file differences"
echo "  • Force overwrite all files: bash $0 $DEPLOY_DIR yes"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
