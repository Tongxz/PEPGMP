# 前端启动脚本 (PowerShell版本)
# Frontend Startup Script (PowerShell Version)

# 设置错误处理
$ErrorActionPreference = "Stop"

# 获取脚本目录和项目根目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$FrontendDir = Join-Path $ProjectRoot "frontend"

# 切换到前端目录
Set-Location $FrontendDir

Write-Host "=== 启动前端开发环境 ===" -ForegroundColor Cyan
Write-Host ""

# 检查 Node.js 是否安装
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Write-Host "Node.js 未安装，请先安装 Node.js" -ForegroundColor Red
    Write-Host "下载地址: https://nodejs.org/" -ForegroundColor Yellow
    exit 1
}

$nodeVersion = node --version
Write-Host "Node.js 版本: $nodeVersion" -ForegroundColor Green

# 检查 npm 是否安装
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCmd) {
    Write-Host "npm 未安装，请先安装 npm" -ForegroundColor Red
    exit 1
}

$npmVersion = npm --version
Write-Host "npm 版本: $npmVersion" -ForegroundColor Green

# 检查 package.json
if (-not (Test-Path "package.json")) {
    Write-Host "package.json 不存在" -ForegroundColor Red
    exit 1
}

# 检查 node_modules 和关键依赖是否存在
$needInstall = $false
$needReinstall = $false

if (-not (Test-Path "node_modules")) {
    $needInstall = $true
} else {
    # 检查 vite 是否安装
    $vitePath = Join-Path "node_modules" ".bin\vite.cmd"
    if (-not (Test-Path $vitePath)) {
        $needInstall = $true
    } else {
        # 检查 rollup 平台特定依赖是否存在（Windows 必需）
        $rollupPlatform = Join-Path "node_modules" "@rollup\rollup-win32-x64-msvc"
        if (-not (Test-Path $rollupPlatform)) {
            Write-Host "检测到缺少平台特定依赖 @rollup/rollup-win32-x64-msvc" -ForegroundColor Yellow
            $needReinstall = $true
        }
    }
}

if ($needReinstall) {
    Write-Host "需要重新安装依赖以包含平台特定包..." -ForegroundColor Yellow
    Write-Host "删除 node_modules 和 package-lock.json..." -ForegroundColor Cyan
    if (Test-Path "node_modules") {
        Remove-Item "node_modules" -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path "package-lock.json") {
        Remove-Item "package-lock.json" -Force -ErrorAction SilentlyContinue
    }
    $needInstall = $true
}

if ($needInstall) {
    Write-Host "正在安装依赖..." -ForegroundColor Yellow
    Write-Host "这可能需要几分钟时间..." -ForegroundColor Yellow
    Write-Host "注意：将安装所有依赖（包括平台特定依赖）..." -ForegroundColor Cyan
    Write-Host ""
    
    # 尝试安装依赖，注意：不使用 --no-optional，因为需要平台特定依赖
    Write-Host "使用 --legacy-peer-deps 安装依赖（包含可选依赖）..." -ForegroundColor Cyan
    & npm install --legacy-peer-deps
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "使用标准方式安装依赖..." -ForegroundColor Yellow
        & npm install
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "依赖安装失败，请手动运行以下命令：" -ForegroundColor Red
            Write-Host "  cd frontend" -ForegroundColor Yellow
            Write-Host "  Remove-Item node_modules, package-lock.json -Recurse -Force" -ForegroundColor Yellow
            Write-Host "  npm install --legacy-peer-deps" -ForegroundColor Yellow
            exit 1
        }
    }
    
    # 验证 rollup 平台依赖是否安装成功
    $rollupPlatform = Join-Path "node_modules" "@rollup\rollup-win32-x64-msvc"
    if (-not (Test-Path $rollupPlatform)) {
        Write-Host "警告：平台特定依赖可能未正确安装" -ForegroundColor Yellow
        Write-Host "尝试手动安装 @rollup/rollup-win32-x64-msvc..." -ForegroundColor Cyan
        & npm install @rollup/rollup-win32-x64-msvc --legacy-peer-deps
    }
    
    Write-Host "依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "依赖已安装" -ForegroundColor Green
}

# 启动开发服务器
Write-Host ""
Write-Host "启动前端开发服务器..." -ForegroundColor Green
Write-Host "访问地址: http://localhost:5173" -ForegroundColor Cyan
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

# 启动 Vite 开发服务器
Write-Host "当前工作目录: $(Get-Location)" -ForegroundColor Gray

# 尝试多种方式启动 vite
$viteJs = Join-Path (Get-Location) "node_modules\vite\bin\vite.js"
$viteCmd = Join-Path (Get-Location) "node_modules\.bin\vite.cmd"

if (Test-Path $viteJs) {
    Write-Host "使用 node 直接运行 vite.js..." -ForegroundColor Cyan
    # 使用 node 直接运行 vite.js（最可靠的方式）
    & node $viteJs
} elseif (Test-Path $viteCmd) {
    Write-Host "使用 vite.cmd 启动..." -ForegroundColor Cyan
    # 使用 vite.cmd
    & $viteCmd
} else {
    Write-Host "本地 vite 未找到，使用 npx 启动..." -ForegroundColor Yellow
    # 如果找不到，尝试使用 npx
    try {
        & npx vite
    } catch {
        Write-Host "启动失败，尝试使用 npm run dev..." -ForegroundColor Yellow
        & npm run dev
    }
}

