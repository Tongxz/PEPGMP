# 仅构建生产环境镜像（不推送、不导出）
# Build production images only (no push, no export)

$ErrorActionPreference = "Stop"

# 获取脚本目录和项目根目录
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR
Set-Location $PROJECT_ROOT

# ==================== 版本号配置 ====================
# 支持通过参数指定版本号，否则使用日期版本号
if ($args.Count -gt 0) {
    $VERSION_TAG = $args[0]
} else {
    $VERSION_TAG = Get-Date -Format "yyyyMMdd"
}
# 也可以使用语义化版本号，例如: v1.0.0, v1.2.3
# if ($args.Count -gt 0) {
#     $VERSION_TAG = $args[0]
# } else {
#     $VERSION_TAG = "v1.0.0"
# }

# 颜色输出函数
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

Write-Host "========================================================================="
Write-Host "                 Build Production Images"
Write-Host "========================================================================="
Write-Host ""
Write-Info "Version Tag: $VERSION_TAG"
Write-Info "Usage: .\build_prod_only.ps1 [version] (e.g., .\build_prod_only.ps1 v1.0.0 or .\build_prod_only.ps1 20250101)"
Write-Host ""

# 检查Docker
try {
    $null = Get-Command docker -ErrorAction Stop
} catch {
    Write-Error "Docker is not installed"
    exit 1
}

try {
    docker info | Out-Null
} catch {
    Write-Error "Docker daemon is not running"
    exit 1
}

Write-Success "Docker environment check passed"
Write-Host ""

# 检查Dockerfile
if (-not (Test-Path "Dockerfile.prod")) {
    Write-Error "Dockerfile.prod does not exist"
    exit 1
}

if (-not (Test-Path "Dockerfile.frontend")) {
    Write-Warning "Dockerfile.frontend does not exist, will skip frontend image build"
    $BUILD_FRONTEND = $false
} else {
    $BUILD_FRONTEND = $true
}

Write-Host "========================================================================="
Write-Host "Preparing to build the following images:"
Write-Host "  1. Backend API image (Dockerfile.prod)"
if ($BUILD_FRONTEND) {
    Write-Host "  2. Frontend image (Dockerfile.frontend)"
}
Write-Host "========================================================================="
Write-Host ""

$confirmation = Read-Host "Confirm to start building? (y/N)"
if ($confirmation -ne "y" -and $confirmation -ne "Y") {
    Write-Warning "Cancelled"
    exit 0
}

Write-Host ""

# ==================== 构建后端镜像 ====================
Write-Info "Starting to build backend API image..."
Write-Info "Dockerfile: Dockerfile.prod"
Write-Info "Image name: pepgmp-backend:$VERSION_TAG"

try {
    # 启用 BuildKit 以支持增量构建优化和缓存挂载
    $env:DOCKER_BUILDKIT = "1"
    docker build -f Dockerfile.prod `
        -t "pepgmp-backend:$VERSION_TAG" `
        -t "pepgmp-backend:latest" `
        .
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Backend API image build completed"
        Write-Info "Created the following tags:"
        docker images "pepgmp-backend:$VERSION_TAG" --format "  {{.Repository}}:{{.Tag}} - {{.Size}}"
        docker images "pepgmp-backend:latest" --format "  {{.Repository}}:{{.Tag}} - {{.Size}}"
    } else {
        throw "Build failed with exit code: $LASTEXITCODE"
    }
} catch {
    Write-Error "Backend API image build failed: $_"
    Write-Host ""
    Write-Warning "If you see '403 Forbidden' or 'failed to resolve source metadata' errors,"
    Write-Warning "this is likely a Docker registry mirror issue."
    Write-Host ""
    Write-Info "Solutions:"
    Write-Host "  1. Update Docker Desktop registry mirrors (Settings > Docker Engine)"
    Write-Host "  2. Try: docker pull python:3.10-slim-bookworm"
    Write-Host "  3. See docs/DOCKER_MIRROR_FIX.md for detailed instructions"
    Write-Host ""
    exit 1
}

Write-Host ""

# ==================== 构建前端镜像 ====================
if ($BUILD_FRONTEND) {
    Write-Info "Starting to build frontend image..."
    Write-Info "Dockerfile: Dockerfile.frontend"
    Write-Info "Image name: pepgmp-frontend:$VERSION_TAG"
    
    # 预先拉取前端构建所需的基础镜像
    Write-Info "Pulling base images for frontend build..."
    try {
        docker pull node:20-alpine 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Failed to pull node:20-alpine, will try during build"
        } else {
            Write-Success "Pulled node:20-alpine"
        }
        
        docker pull nginx:1.27-alpine 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Failed to pull nginx:1.27-alpine, will try during build"
        } else {
            Write-Success "Pulled nginx:1.27-alpine"
        }
    } catch {
        Write-Warning "Pre-pulling base images failed, will try during build: $_"
    }
    Write-Host ""

    try {
        # 启用 BuildKit 以支持增量构建优化和缓存挂载
        $env:DOCKER_BUILDKIT = "1"
        docker build -f Dockerfile.frontend `
            --build-arg VITE_API_BASE=/api/v1 `
            --build-arg BASE_URL=/ `
            --build-arg SKIP_TYPE_CHECK=true `
            -t "pepgmp-frontend:$VERSION_TAG" `
            -t "pepgmp-frontend:latest" `
            .
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Frontend image build completed"
            Write-Info "Created the following tags:"
            docker images "pepgmp-frontend:$VERSION_TAG" --format "  {{.Repository}}:{{.Tag}} - {{.Size}}"
            docker images "pepgmp-frontend:latest" --format "  {{.Repository}}:{{.Tag}} - {{.Size}}"
        } else {
            throw "Build failed with exit code: $LASTEXITCODE"
        }
    } catch {
        Write-Error "Frontend image build failed: $_"
        Write-Host ""
        Write-Warning "If you see '403 Forbidden' or 'failed to resolve source metadata' errors,"
        Write-Warning "this is likely a Docker registry mirror issue for frontend base images."
        Write-Host ""
        Write-Info "Solutions:"
        Write-Host "  1. Update Docker Desktop registry mirrors (Settings > Docker Engine)"
        Write-Host "  2. Manually pull base images:"
        Write-Host "     docker pull node:20-alpine"
        Write-Host "     docker pull nginx:1.27-alpine"
        Write-Host "  3. Then re-run: .\scripts\build_prod_only.ps1 $VERSION_TAG"
        Write-Host "  4. See docs/DOCKER_MIRROR_FIX.md for detailed instructions"
        Write-Host ""
        exit 1
    }

    Write-Host ""
}

# ==================== 显示构建结果 ====================
Write-Success "========================================================================="
Write-Success "                     Build Completed"
Write-Success "========================================================================="
Write-Host ""
Write-Info "Built images:"
docker images | Select-String -Pattern "pepgmp-(backend|frontend)" | ForEach-Object { Write-Host $_.Line }
Write-Host ""

# 自动更新 .env.production 中的版本号
if (Test-Path ".env.production") {
    Write-Info "Auto-updating image version in .env.production..."
    try {
        & "$SCRIPT_DIR\update_image_version.ps1" $VERSION_TAG
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Version number has been auto-updated"
        } else {
            throw "Update failed with exit code: $LASTEXITCODE"
        }
    } catch {
        Write-Warning "Auto-update version failed, please run manually: .\scripts\update_image_version.ps1 $VERSION_TAG"
    }
    Write-Host ""
}

Write-Info "Next steps:"
Write-Host "  1. Start with Docker Compose (version already updated):"
Write-Host "     docker compose -f docker-compose.prod.yml up -d"
Write-Host ""
Write-Host "  2. Or run containers manually (recommended to use version tag):"
Write-Host "     docker run -d --name pepgmp-api-prod -p 8000:8000 pepgmp-backend:$VERSION_TAG"
if ($BUILD_FRONTEND) {
    Write-Host "     docker run -d --name pepgmp-frontend-prod -p 8080:80 pepgmp-frontend:$VERSION_TAG"
}
Write-Host ""
Write-Host "  3. Push to Registry (if needed):"
Write-Host "     .\scripts\push_to_registry.ps1 $VERSION_TAG"
Write-Host ""
$warningMsg = "Note: Production environment recommends using version tag (" + $VERSION_TAG + ") instead of :latest"
Write-Warning $warningMsg
Write-Host ""
