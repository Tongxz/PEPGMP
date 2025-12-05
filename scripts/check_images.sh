#!/bin/bash

################################################################################
# Check Docker Images
# Purpose: Check if Docker images are available and match configuration
################################################################################

echo "========================================================================="
echo "Checking Docker Images"
echo "========================================================================="
echo ""

# Check backend images
echo "Backend images:"
BACKEND_IMAGES=$(docker images | grep pepgmp-backend || echo "")
if [ -z "$BACKEND_IMAGES" ]; then
    echo "  [NOT FOUND] No backend images found"
else
    echo "$BACKEND_IMAGES" | while read line; do
        echo "  $line"
    done
fi
echo ""

# Check frontend images
echo "Frontend images:"
FRONTEND_IMAGES=$(docker images | grep pepgmp-frontend || echo "")
if [ -z "$FRONTEND_IMAGES" ]; then
    echo "  [NOT FOUND] No frontend images found"
else
    echo "$FRONTEND_IMAGES" | while read line; do
        echo "  $line"
    done
fi
echo ""

# Check .env.production IMAGE_TAG
echo "========================================================================="
echo "Checking .env.production IMAGE_TAG:"
echo "========================================================================="
if [ -f ".env.production" ]; then
    IMAGE_TAG=$(grep "^IMAGE_TAG=" .env.production | cut -d'=' -f2)
    echo "  IMAGE_TAG in .env.production: $IMAGE_TAG"
    echo ""

    # Check if image with this tag exists
    if docker images | grep -q "pepgmp-backend.*$IMAGE_TAG"; then
        echo "  [OK] Backend image with tag '$IMAGE_TAG' found"
    else
        echo "  [WARNING] Backend image with tag '$IMAGE_TAG' NOT found"
        echo "  Available backend tags:"
        docker images | grep pepgmp-backend | awk '{print "    - " $2}' || echo "    (none)"
    fi
else
    echo "  [NOT FOUND] .env.production file not found in current directory"
fi
echo ""

# Summary
echo "========================================================================="
echo "Summary"
echo "========================================================================="
BACKEND_COUNT=$(docker images | grep -c pepgmp-backend || echo "0")
FRONTEND_COUNT=$(docker images | grep -c pepgmp-frontend || echo "0")

echo "Backend images: $BACKEND_COUNT"
echo "Frontend images: $FRONTEND_COUNT"
echo ""

if [ "$BACKEND_COUNT" -eq "0" ]; then
    echo "[WARNING] No backend images found. You may need to:"
    echo "  1. Build images: bash scripts/build_prod_only.sh 20251201"
    echo "  2. Or import images from Windows"
else
    echo "[OK] Backend images are available"
fi

echo "========================================================================="
