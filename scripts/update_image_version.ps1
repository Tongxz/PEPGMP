# 自动更新生产环境镜像版本号
# Auto-update production image version in .env.production

$ErrorActionPreference = "Stop"

# 获取脚本目录和项目根目录
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR
Set-Location $PROJECT_ROOT

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

$ENV_FILE = ".env.production"

# 检查 .env.production 是否存在
if (-not (Test-Path $ENV_FILE)) {
    Write-Error ".env.production 文件不存在"
    exit 1
}

# 获取参数：版本号（可选）
if ($args.Count -gt 0) {
    $VERSION_TAG = $args[0]
} else {
    $VERSION_TAG = "auto"
}

# 如果未指定版本号，自动查找最新的日期版本号镜像
if ($VERSION_TAG -eq "auto") {
    Write-Info "自动查找最新的日期版本号镜像..."

    try {
        # 查找所有 pepgmp-backend 镜像的日期版本号（格式：YYYYMMDD）
        $allTags = docker images pepgmp-backend --format "{{.Tag}}" 2>$null
        $dateTags = $allTags | Where-Object { $_ -match '^\d{8}$' } | Sort-Object -Descending

        if ($dateTags.Count -gt 0) {
            $LATEST_TAG = $dateTags[0]
        } else {
            Write-Warning "未找到日期版本号镜像，尝试查找所有版本..."
            # 查找所有非 latest 的标签
            $nonLatestTags = $allTags | Where-Object { $_ -ne "latest" } | Sort-Object -Descending
            if ($nonLatestTags.Count -gt 0) {
                $LATEST_TAG = $nonLatestTags[0]
            }
        }

        if ([string]::IsNullOrEmpty($LATEST_TAG)) {
            Write-Error "未找到可用的镜像版本"
            Write-Info "请先构建镜像: .\scripts\build_prod_only.ps1"
            exit 1
        }

        $VERSION_TAG = $LATEST_TAG
        Write-Info "找到最新版本: $VERSION_TAG"
    } catch {
        Write-Error "查找镜像版本失败: $_"
        exit 1
    }
}

# 更新 .env.production 中的 IMAGE_TAG
Write-Info "更新 $ENV_FILE 中的 IMAGE_TAG=$VERSION_TAG..."

try {
    $content = Get-Content $ENV_FILE -Raw
    $lines = Get-Content $ENV_FILE

    # 检查是否已存在 IMAGE_TAG
    $hasImageTag = $false
    $newLines = @()

    foreach ($line in $lines) {
        if ($line -match '^IMAGE_TAG=') {
            $newLines += "IMAGE_TAG=$VERSION_TAG"
            $hasImageTag = $true
        } else {
            $newLines += $line
        }
    }

    if (-not $hasImageTag) {
        # 添加新行
        if ($newLines.Count -gt 0 -and $newLines[-1] -ne "") {
            $newLines += ""
        }
        $newLines += "# Docker镜像版本号（自动更新）"
        $newLines += "IMAGE_TAG=$VERSION_TAG"
        Write-Success "已添加 IMAGE_TAG=$VERSION_TAG"
    } else {
        Write-Success "已更新 IMAGE_TAG=$VERSION_TAG"
    }

    # 写入文件
    $newLines | Set-Content $ENV_FILE -NoNewline:$false

} catch {
    Write-Error "更新文件失败: $_"
    exit 1
}

Write-Host ""
Write-Success "========================================================================="
Write-Success "                     版本号更新完成"
Write-Success "========================================================================="
Write-Host ""
Write-Info "当前配置:"
Write-Host "  IMAGE_TAG=$VERSION_TAG"
Write-Host ""
Write-Info "下一步:"
Write-Host "  1. 使用 Docker Compose 启动:"
Write-Host "     docker compose -f docker-compose.prod.yml up -d"
Write-Host ""
Write-Host "  2. 验证使用的镜像版本:"
Write-Host "     docker compose -f docker-compose.prod.yml config | Select-String image"
Write-Host ""
