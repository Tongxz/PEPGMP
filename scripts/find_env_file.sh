#!/bin/bash

################################################################################
# Find .env.production file
# Purpose: Help locate the .env.production file after generation
################################################################################

echo "========================================================================="
echo "Searching for .env.production file..."
echo "========================================================================="
echo ""

# Get current directory
CURRENT_DIR=$(pwd)
echo "Current directory: $CURRENT_DIR"
echo ""

# Check in current directory
if [ -f ".env.production" ]; then
    echo "[FOUND] .env.production exists in current directory"
    echo "  Path: $CURRENT_DIR/.env.production"
    ls -lh .env.production
    echo ""
    echo "File permissions:"
    stat -c "%a %n" .env.production
    echo ""
    echo "First few lines:"
    head -5 .env.production
else
    echo "[NOT FOUND] .env.production does not exist in current directory"
fi

echo ""
echo "========================================================================="
echo "Searching in parent directories..."
echo "========================================================================="

# Search in parent directories (up to 3 levels)
PARENT_DIR="$CURRENT_DIR"
for i in {1..3}; do
    if [ -f "$PARENT_DIR/.env.production" ]; then
        echo "[FOUND] .env.production exists in: $PARENT_DIR"
        ls -lh "$PARENT_DIR/.env.production"
        break
    fi
    PARENT_DIR=$(dirname "$PARENT_DIR")
done

echo ""
echo "========================================================================="
echo "Searching for backup files..."
echo "========================================================================="

# Find backup files
find . -name ".env.production.backup*" -type f 2>/dev/null | head -5

echo ""
echo "========================================================================="
echo "Searching for credentials file..."
echo "========================================================================="

if [ -f ".env.production.credentials" ]; then
    echo "[FOUND] .env.production.credentials exists"
    ls -lh .env.production.credentials
else
    echo "[NOT FOUND] .env.production.credentials does not exist"
fi

echo ""
echo "========================================================================="
echo "Checking file system..."
echo "========================================================================="

# Check if we're in WSL
if [ -d "/mnt/c" ] || [ -d "/mnt/f" ]; then
    echo "Running in WSL environment"
    echo ""
    echo "If you ran the script from Windows path (/mnt/f/...),"
    echo "the file should be in: $CURRENT_DIR/.env.production"
    echo ""
    echo "Try:"
    echo "  cd $CURRENT_DIR"
    echo "  ls -la .env.production"
    echo "  cat .env.production | head -20"
fi

echo ""
echo "========================================================================="

