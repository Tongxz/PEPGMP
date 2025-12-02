#!/bin/bash

################################################################################
# Fix Nginx File Permissions
# Purpose: Fix file permissions for nginx directory and files
################################################################################

set -e

DEPLOY_DIR="${1:-$HOME/projects/Pyt}"

echo "========================================================================="
echo "Fix Nginx File Permissions"
echo "========================================================================="
echo ""
echo "Deploy directory: $DEPLOY_DIR"
echo ""

# Check if deploy directory exists
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "ERROR: Deploy directory does not exist: $DEPLOY_DIR"
    exit 1
fi

cd "$DEPLOY_DIR"

# Check if nginx directory exists
if [ ! -d "nginx" ]; then
    echo "Creating nginx directory..."
    mkdir -p nginx/ssl
fi

# Fix permissions
echo "Fixing permissions..."

# Ensure current user owns the files first (requires sudo)
if [ -d "nginx" ]; then
    CURRENT_USER=$(whoami)
    echo "Changing ownership of nginx directory to $CURRENT_USER (requires sudo)..."
    sudo chown -R "$CURRENT_USER:$CURRENT_USER" nginx/
    echo "[OK] Changed ownership of nginx directory to $CURRENT_USER"
fi

# Fix directory permissions
if [ -d "nginx" ]; then
    chmod 755 nginx
    echo "[OK] Fixed nginx directory permissions"
fi

if [ -d "nginx/ssl" ]; then
    chmod 755 nginx/ssl
    echo "[OK] Fixed nginx/ssl directory permissions"
fi

# Fix file permissions
if [ -f "nginx/nginx.conf" ]; then
    # Remove file if owned by root
    if [ ! -w "nginx/nginx.conf" ]; then
        echo "WARNING: nginx.conf is not writable, removing..."
        sudo rm -f nginx/nginx.conf
    fi
    if [ -f "nginx/nginx.conf" ]; then
        chmod 644 nginx/nginx.conf
        echo "[OK] Fixed nginx.conf permissions"
    fi
fi

echo ""
echo "========================================================================="
echo "Permissions Fixed"
echo "========================================================================="
echo ""
echo "Next step:"
echo "  bash scripts/prepare_minimal_deploy.sh ~/projects/Pyt yes"
echo ""
echo "========================================================================="

