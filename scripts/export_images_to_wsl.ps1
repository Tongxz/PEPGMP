# Export Docker Images to WSL2
# Purpose: Export Docker images from Windows to WSL2 Ubuntu for 1Panel deployment

$ErrorActionPreference = "Stop"

# Get script directory and project root
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR
Set-Location $PROJECT_ROOT

# ==================== Version Tag Configuration ====================
# Support version tag via parameter, otherwise use date version
if ($args.Count -gt 0) {
    $VERSION_TAG = $args[0]
} else {
    $VERSION_TAG = Get-Date -Format "yyyyMMdd"
}

Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "Export Docker Images to WSL2" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Version Tag: $VERSION_TAG" -ForegroundColor Yellow
Write-Host ""

# Check if images exist
Write-Host "Checking Docker images..." -ForegroundColor Blue
$BACKEND_IMAGE = "pepgmp-backend:$VERSION_TAG"
$FRONTEND_IMAGE = "pepgmp-frontend:$VERSION_TAG"

$backendExists = docker images $BACKEND_IMAGE --format "{{.Repository}}:{{.Tag}}" 2>$null
$frontendExists = docker images $FRONTEND_IMAGE --format "{{.Repository}}:{{.Tag}}" 2>$null

if (-not $backendExists) {
    Write-Host "[ERROR] Backend image not found: $BACKEND_IMAGE" -ForegroundColor Red
    Write-Host ""
    Write-Host "Available backend images:" -ForegroundColor Yellow
    docker images pepgmp-backend --format "  {{.Repository}}:{{.Tag}}"
    Write-Host ""
    Write-Host "Please build the image first or specify the correct tag:" -ForegroundColor Yellow
    Write-Host "  .\scripts\build_prod_only.ps1 $VERSION_TAG" -ForegroundColor Cyan
    exit 1
}

Write-Host "[OK] Backend image found: $BACKEND_IMAGE" -ForegroundColor Green

if ($frontendExists) {
    Write-Host "[OK] Frontend image found: $FRONTEND_IMAGE" -ForegroundColor Green
} else {
    Write-Host "[INFO] Frontend image not found: $FRONTEND_IMAGE (optional)" -ForegroundColor Yellow
}

Write-Host ""

# Set export directory
$EXPORT_DIR = Join-Path $PROJECT_ROOT "docker-images"
if (-not (Test-Path $EXPORT_DIR)) {
    New-Item -ItemType Directory -Path $EXPORT_DIR | Out-Null
    Write-Host "[OK] Created export directory: $EXPORT_DIR" -ForegroundColor Green
}

Write-Host "Export directory: $EXPORT_DIR" -ForegroundColor Blue
Write-Host ""

# ==================== Export Backend Image ====================
$BACKEND_TAR = Join-Path $EXPORT_DIR "pepgmp-backend-$VERSION_TAG.tar"
Write-Host "Exporting backend image..." -ForegroundColor Blue
Write-Host "  Image: $BACKEND_IMAGE" -ForegroundColor Gray
Write-Host "  Output: $BACKEND_TAR" -ForegroundColor Gray

try {
    docker save $BACKEND_IMAGE -o $BACKEND_TAR
    if ($LASTEXITCODE -eq 0) {
        $size = (Get-Item $BACKEND_TAR).Length / 1MB
        Write-Host "[OK] Backend image exported successfully" -ForegroundColor Green
        Write-Host "  Size: $([math]::Round($size, 2)) MB" -ForegroundColor Gray
    } else {
        throw "Export failed with exit code: $LASTEXITCODE"
    }
} catch {
    Write-Host "[ERROR] Failed to export backend image: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ==================== Export Frontend Image (if exists) ====================
if ($frontendExists) {
    $FRONTEND_TAR = Join-Path $EXPORT_DIR "pepgmp-frontend-$VERSION_TAG.tar"
    Write-Host "Exporting frontend image..." -ForegroundColor Blue
    Write-Host "  Image: $FRONTEND_IMAGE" -ForegroundColor Gray
    Write-Host "  Output: $FRONTEND_TAR" -ForegroundColor Gray

    try {
        docker save $FRONTEND_IMAGE -o $FRONTEND_TAR
        if ($LASTEXITCODE -eq 0) {
            $size = (Get-Item $FRONTEND_TAR).Length / 1MB
            Write-Host "[OK] Frontend image exported successfully" -ForegroundColor Green
            Write-Host "  Size: $([math]::Round($size, 2)) MB" -ForegroundColor Gray
        } else {
            throw "Export failed with exit code: $LASTEXITCODE"
        }
    } catch {
        Write-Host "[ERROR] Failed to export frontend image: $_" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# ==================== Summary ====================
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "Export Complete" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Exported files:" -ForegroundColor Blue
Write-Host "  $BACKEND_TAR" -ForegroundColor Gray
if ($frontendExists) {
    Write-Host "  $FRONTEND_TAR" -ForegroundColor Gray
}
Write-Host ""

# WSL2 path
$WSL_PROJECT_PATH = "/mnt/f/code/PythonCode/Pyt"
$WSL_EXPORT_DIR = "$WSL_PROJECT_PATH/docker-images"

Write-Host "Next steps (in WSL2 Ubuntu):" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Import backend image:" -ForegroundColor Cyan
Write-Host "   cd $WSL_EXPORT_DIR" -ForegroundColor Gray
Write-Host "   docker load -i pepgmp-backend-$VERSION_TAG.tar" -ForegroundColor Gray
Write-Host ""
if ($frontendExists) {
    Write-Host "2. Import frontend image:" -ForegroundColor Cyan
    Write-Host "   docker load -i pepgmp-frontend-$VERSION_TAG.tar" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Verify images:" -ForegroundColor Cyan
} else {
    Write-Host "2. Verify images:" -ForegroundColor Cyan
}
Write-Host "   docker images | grep pepgmp" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Ensure IMAGE_TAG in .env.production matches:" -ForegroundColor Cyan
Write-Host "   grep IMAGE_TAG ~/projects/Pyt/.env.production" -ForegroundColor Gray
Write-Host "   (Should show: IMAGE_TAG=$VERSION_TAG)" -ForegroundColor Gray
Write-Host ""
Write-Host "=========================================================================" -ForegroundColor Cyan

