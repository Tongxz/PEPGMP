#!/bin/bash

################################################################################
# Import Docker Images from Windows Export
# Purpose: Import Docker images exported from Windows to WSL2 Ubuntu
################################################################################

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "========================================================================="
echo -e "${CYAN}Import Docker Images from Windows${NC}"
echo "========================================================================="
echo ""

# Get version tag from parameter or .env.production
if [ -n "$1" ]; then
    VERSION_TAG="$1"
elif [ -f ".env.production" ]; then
    VERSION_TAG=$(grep "^IMAGE_TAG=" .env.production | cut -d'=' -f2)
    echo -e "${YELLOW}Using IMAGE_TAG from .env.production: $VERSION_TAG${NC}"
else
    echo -e "${RED}Error: No version tag specified and .env.production not found${NC}"
    echo ""
    echo "Usage: bash scripts/import_images_from_windows.sh [VERSION_TAG]"
    echo "Example: bash scripts/import_images_from_windows.sh 20251201"
    exit 1
fi

echo ""
echo "Version Tag: $VERSION_TAG"
echo ""

# Set import directory (Windows project path in WSL)
WINDOWS_PROJECT_PATH="/mnt/f/code/PythonCode/PEPGMP"
IMPORT_DIR="$WINDOWS_PROJECT_PATH/docker-images"

if [ ! -d "$IMPORT_DIR" ]; then
    echo -e "${RED}Error: Import directory not found: $IMPORT_DIR${NC}"
    echo ""
    echo "Please export images from Windows first:"
    echo "  .\scripts\export_images_to_wsl.ps1 $VERSION_TAG"
    exit 1
fi

echo "Import directory: $IMPORT_DIR"
echo ""

# ==================== Import Backend Image ====================
BACKEND_TAR="$IMPORT_DIR/pepgmp-backend-$VERSION_TAG.tar"

if [ ! -f "$BACKEND_TAR" ]; then
    echo -e "${RED}Error: Backend image file not found: $BACKEND_TAR${NC}"
    echo ""
    echo "Available files in $IMPORT_DIR:"
    ls -lh "$IMPORT_DIR"/*.tar 2>/dev/null || echo "  (none)"
    exit 1
fi

echo -e "${BLUE}Importing backend image...${NC}"
echo "  File: $BACKEND_TAR"
FILE_SIZE=$(du -h "$BACKEND_TAR" | cut -f1)
echo "  Size: $FILE_SIZE"
echo ""

docker load -i "$BACKEND_TAR"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}[OK] Backend image imported successfully${NC}"
else
    echo -e "${RED}[ERROR] Failed to import backend image${NC}"
    exit 1
fi

echo ""

# ==================== Import Frontend Image (if exists) ====================
FRONTEND_TAR="$IMPORT_DIR/pepgmp-frontend-$VERSION_TAG.tar"

if [ -f "$FRONTEND_TAR" ]; then
    echo -e "${BLUE}Importing frontend image...${NC}"
    echo "  File: $FRONTEND_TAR"
    FILE_SIZE=$(du -h "$FRONTEND_TAR" | cut -f1)
    echo "  Size: $FILE_SIZE"
    echo ""

    docker load -i "$FRONTEND_TAR"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK] Frontend image imported successfully${NC}"
    else
        echo -e "${RED}[ERROR] Failed to import frontend image${NC}"
        exit 1
    fi
    echo ""
fi

# ==================== Verify Images ====================
echo "========================================================================="
echo -e "${CYAN}Verifying imported images${NC}"
echo "========================================================================="
echo ""

echo "Backend images:"
docker images | grep pepgmp-backend || echo "  (none)"
echo ""

if [ -f "$FRONTEND_TAR" ]; then
    echo "Frontend images:"
    docker images | grep pepgmp-frontend || echo "  (none)"
    echo ""
fi

# Check if image with correct tag exists
if docker images | grep -q "pepgmp-backend.*$VERSION_TAG"; then
    echo -e "${GREEN}[OK] Backend image with tag '$VERSION_TAG' found${NC}"
else
    echo -e "${YELLOW}[WARNING] Backend image with tag '$VERSION_TAG' not found${NC}"
    echo "Available backend tags:"
    docker images | grep pepgmp-backend | awk '{print "  - " $2}' || echo "  (none)"
fi
echo ""

# Check .env.production IMAGE_TAG
if [ -f ".env.production" ]; then
    ENV_IMAGE_TAG=$(grep "^IMAGE_TAG=" .env.production | cut -d'=' -f2)
    if [ "$ENV_IMAGE_TAG" = "$VERSION_TAG" ]; then
        echo -e "${GREEN}[OK] IMAGE_TAG in .env.production matches: $ENV_IMAGE_TAG${NC}"
    else
        echo -e "${YELLOW}[WARNING] IMAGE_TAG mismatch:${NC}"
        echo "  .env.production: $ENV_IMAGE_TAG"
        echo "  Imported tag: $VERSION_TAG"
        echo ""
        echo "You may need to update .env.production:"
        echo "  sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=$VERSION_TAG/' .env.production"
    fi
else
    echo -e "${YELLOW}[INFO] .env.production not found in current directory${NC}"
fi

echo ""
echo "========================================================================="
echo -e "${GREEN}Import Complete${NC}"
echo "========================================================================="
echo ""
echo "Next steps:"
echo "  1. Verify configuration:"
echo "     cd ~/projects/PEPGMP
echo "     docker-compose -f docker-compose.prod.yml --env-file .env.production config"
echo ""
echo "  2. Deploy in 1Panel:"
echo "     - Create Compose project"
echo "     - Working directory: ~/projects/PEPGMP
echo "     - Compose file: docker-compose.prod.yml"
echo ""
echo "========================================================================="
