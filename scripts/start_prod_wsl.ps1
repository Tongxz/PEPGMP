# WSL 生产环境启动脚本 (Windows PowerShell 入口)
# WSL Production Environment Startup Script (Windows PowerShell Entry Point)
# 此脚本在 Windows PowerShell 中运行，自动切换到 WSL 并执行 bash 脚本

$ErrorActionPreference = "Stop"

# 获取脚本目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "                     启动生产环境 (WSL)" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ""

# 检查 WSL 是否安装
$wslInstalled = $false
try {
    $wslVersion = wsl --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $wslInstalled = $true
    }
} catch {
    # WSL 可能未安装或版本较旧
}

if (-not $wslInstalled) {
    # 尝试检查 WSL 是否可用（旧版本）
    try {
        $wslList = wsl --list 2>&1
        if ($LASTEXITCODE -eq 0) {
            $wslInstalled = $true
        }
    } catch {
        Write-Host "❌ WSL 未安装或不可用" -ForegroundColor Red
        Write-Host ""
        Write-Host "安装步骤：" -ForegroundColor Yellow
        Write-Host "  1. 以管理员身份运行 PowerShell" -ForegroundColor Cyan
        Write-Host "  2. 执行: wsl --install" -ForegroundColor Cyan
        Write-Host "  3. 重启计算机" -ForegroundColor Cyan
        Write-Host "  4. 安装 Linux 发行版（如 Ubuntu）" -ForegroundColor Cyan
        exit 1
    }
}

# 获取默认 WSL 发行版
$wslDistro = $null
try {
    $wslList = wsl --list --quiet 2>&1
    if ($LASTEXITCODE -eq 0 -and $wslList) {
        # 获取第一个可用的发行版
        $wslDistro = ($wslList -split "`n" | Where-Object { $_ -match '\S' } | Select-Object -First 1).Trim()
    }
} catch {
    # 使用默认发行版
}

if (-not $wslDistro) {
    Write-Host "⚠️  未找到 WSL 发行版，使用默认发行版" -ForegroundColor Yellow
}

# 检查 Docker Desktop WSL 集成
Write-Host "检查 Docker Desktop WSL 集成..." -ForegroundColor Cyan
$dockerInWsl = $false
try {
    if ($wslDistro) {
        $dockerCheck = wsl -d $wslDistro docker --version 2>&1
    } else {
        $dockerCheck = wsl docker --version 2>&1
    }
    if ($LASTEXITCODE -eq 0) {
        $dockerInWsl = $true
        Write-Host "✅ Docker 在 WSL 中可用" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Docker 在 WSL 中不可用" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "请确保：" -ForegroundColor Yellow
    Write-Host "  1. Docker Desktop 已安装并运行" -ForegroundColor Cyan
    Write-Host "  2. 在 Docker Desktop Settings > General 中启用 'Use the WSL 2 based engine'" -ForegroundColor Cyan
    Write-Host "  3. 在 Docker Desktop Settings > Resources > WSL Integration 中启用当前 WSL 发行版" -ForegroundColor Cyan
    Write-Host ""
    $continue = Read-Host "是否继续？(y/n)"
    if ($continue -notmatch "^[yY]") {
        exit 1
    }
}

Write-Host ""

# 转换 Windows 路径为 WSL 路径
$wslProjectRoot = if ($wslDistro) {
    wsl -d $wslDistro wslpath -a $ProjectRoot 2>&1
} else {
    wsl wslpath -a $ProjectRoot 2>&1
}

if ($LASTEXITCODE -ne 0) {
    # 如果 wslpath 不可用，尝试手动转换
    $wslProjectRoot = $ProjectRoot -replace '^([A-Z]):', '/mnt/$1' -replace '\\', '/' -replace '^([A-Z])', {$_.Value.ToLower()}
}

Write-Host "项目路径 (WSL): $wslProjectRoot" -ForegroundColor Cyan
Write-Host ""

# 检查 bash 脚本是否存在
$bashScript = Join-Path $ScriptDir "start_prod_wsl.sh"
if (-not (Test-Path $bashScript)) {
    Write-Host "❌ WSL 启动脚本不存在: $bashScript" -ForegroundColor Red
    exit 1
}

# 确保 bash 脚本有执行权限
Write-Host "设置脚本执行权限..." -ForegroundColor Cyan
if ($wslDistro) {
    wsl -d $wslDistro chmod +x "$wslProjectRoot/scripts/start_prod_wsl.sh" 2>&1 | Out-Null
} else {
    wsl chmod +x "$wslProjectRoot/scripts/start_prod_wsl.sh" 2>&1 | Out-Null
}

Write-Host ""

# 在 WSL 中执行 bash 脚本
Write-Host "在 WSL 中启动生产环境..." -ForegroundColor Cyan
Write-Host ""

if ($wslDistro) {
    wsl -d $wslDistro bash -c "cd '$wslProjectRoot' && bash scripts/start_prod_wsl.sh"
} else {
    wsl bash -c "cd '$wslProjectRoot' && bash scripts/start_prod_wsl.sh"
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ 启动失败" -ForegroundColor Red
    exit 1
}

