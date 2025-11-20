# 生产环境启动脚本 (PowerShell版本)
# Production Environment Startup Script (PowerShell Version)

# 设置错误处理
$ErrorActionPreference = "Stop"

# 检查PowerShell执行策略
$executionPolicy = Get-ExecutionPolicy
if ($executionPolicy -eq "Restricted") {
    Write-Host "PowerShell执行策略受限，需要设置执行策略" -ForegroundColor Yellow
    Write-Host "请以管理员身份运行以下命令之一：" -ForegroundColor Yellow
    Write-Host "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Cyan
    Write-Host "或者" -ForegroundColor Yellow
    Write-Host "Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process" -ForegroundColor Cyan
    Write-Host ""
    $bypass = Read-Host "是否临时绕过执行策略运行此脚本？(y/n)"
    if ($bypass -match "^[yY]") {
        Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
    } else {
        exit 1
    }
}

# 获取脚本目录和项目根目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# 切换到项目根目录
Set-Location $ProjectRoot

Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "                     启动生产环境 (Windows)" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ""

# 检查是否为管理员
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) {
    Write-Host "⚠️  警告：不建议使用管理员权限运行" -ForegroundColor Yellow
    $continue = Read-Host "继续？(y/n)"
    if ($continue -notmatch "^[yY]") {
        exit 1
    }
}

# 检查.env.production文件
if (-not (Test-Path ".env.production")) {
    Write-Host ".env.production文件不存在" -ForegroundColor Red
    Write-Host ""
    if (Test-Path ".env.production.example") {
        Write-Host "创建步骤：" -ForegroundColor Yellow
        Write-Host "  1. Copy-Item .env.production.example .env.production" -ForegroundColor Cyan
        Write-Host "  2. 编辑.env.production并设置强密码" -ForegroundColor Cyan
        Write-Host "  3. icacls .env.production /inheritance:r /grant:r `"$env:USERNAME:R`"" -ForegroundColor Cyan
    }
    exit 1
}

# 检查文件权限（Windows ACL）
$acl = Get-Acl .env.production
$hasRestrictedAccess = $true
foreach ($access in $acl.Access) {
    if ($access.IdentityReference -eq "BUILTIN\Users" -and $access.FileSystemRights -match "FullControl|Modify|Write") {
        $hasRestrictedAccess = $false
        break
    }
}
if (-not $hasRestrictedAccess) {
    Write-Host "⚠️  警告：.env.production文件权限不安全" -ForegroundColor Yellow
    $fixPerms = Read-Host "是否限制访问权限？(y/n)"
    if ($fixPerms -match "^[yY]") {
        try {
            icacls .env.production /inheritance:r /grant:r "${env:USERNAME}:(R)" 2>&1 | Out-Null
            Write-Host "✅ 权限已更新" -ForegroundColor Green
        } catch {
            Write-Host "⚠️  无法更新权限，请手动设置" -ForegroundColor Yellow
        }
    }
}

# 设置环境
$env:ENVIRONMENT = "production"

# 加载生产环境配置
Write-Host "加载生产环境配置..." -ForegroundColor Cyan
if (Test-Path ".env.production") {
    Get-Content ".env.production" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)\s*=\s*(.*)\s*$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            if ($value -match '^"(.*)"$') {
                $value = $matches[1]
            } elseif ($value -match "^'(.*)'$") {
                $value = $matches[1]
            }
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}
Write-Host "✅ 已加载生产环境配置" -ForegroundColor Green
Write-Host ""

# 验证配置
Write-Host "验证配置..." -ForegroundColor Cyan
try {
    $validateOut = Join-Path $env:TEMP "validate_config_out_$PID.txt"
    $validateErr = Join-Path $env:TEMP "validate_config_err_$PID.txt"
    $validateProcess = Start-Process -FilePath "python" -ArgumentList "scripts/validate_config.py" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $validateOut -RedirectStandardError $validateErr
    if ($validateProcess.ExitCode -eq 0) {
        Write-Host "✅ 配置验证通过" -ForegroundColor Green
    } else {
        throw "Config validation failed"
    }
    Remove-Item $validateOut -ErrorAction SilentlyContinue
    Remove-Item $validateErr -ErrorAction SilentlyContinue
} catch {
    Write-Host "❌ 配置验证失败，请检查.env.production文件" -ForegroundColor Red
    Write-Host "错误详情: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 检查必需的服务
Write-Host "检查依赖服务..." -ForegroundColor Cyan

# 检查Docker
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Host "❌ Docker未安装或未在PATH中" -ForegroundColor Red
    Write-Host "请安装Docker Desktop: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    exit 1
}

# 检查Docker是否运行
$dockerOut = Join-Path $env:TEMP "docker_info_out_$PID.txt"
$dockerErr = Join-Path $env:TEMP "docker_info_err_$PID.txt"
$dockerInfoProcess = Start-Process -FilePath "docker" -ArgumentList "info" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $dockerOut -RedirectStandardError $dockerErr
$dockerRunning = ($dockerInfoProcess.ExitCode -eq 0)
Remove-Item $dockerOut -ErrorAction SilentlyContinue
Remove-Item $dockerErr -ErrorAction SilentlyContinue

if (-not $dockerRunning) {
    Write-Host "❌ Docker未运行，请启动Docker Desktop" -ForegroundColor Red
    Write-Host "等待Docker启动..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    $dockerOut = Join-Path $env:TEMP "docker_info_out_$PID.txt"
    $dockerErr = Join-Path $env:TEMP "docker_info_err_$PID.txt"
    $dockerInfoProcess = Start-Process -FilePath "docker" -ArgumentList "info" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $dockerOut -RedirectStandardError $dockerErr
    $dockerRunning = ($dockerInfoProcess.ExitCode -eq 0)
    Remove-Item $dockerOut -ErrorAction SilentlyContinue
    Remove-Item $dockerErr -ErrorAction SilentlyContinue
    
    if (-not $dockerRunning) {
        Write-Host "❌ Docker仍未就绪，请手动启动Docker Desktop后重试" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✅ Docker运行中" -ForegroundColor Green

# 检查Docker Compose
$dockerComposeCmd = Get-Command docker-compose -ErrorAction SilentlyContinue
if (-not $dockerComposeCmd) {
    # 尝试使用 docker compose (v2)
    $dockerComposeV2Out = Join-Path $env:TEMP "docker_compose_v2_out_$PID.txt"
    $dockerComposeV2Err = Join-Path $env:TEMP "docker_compose_v2_err_$PID.txt"
    $dockerComposeV2Process = Start-Process -FilePath "docker" -ArgumentList "compose", "version" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $dockerComposeV2Out -RedirectStandardError $dockerComposeV2Err
    $hasDockerComposeV2 = ($dockerComposeV2Process.ExitCode -eq 0)
    Remove-Item $dockerComposeV2Out -ErrorAction SilentlyContinue
    Remove-Item $dockerComposeV2Err -ErrorAction SilentlyContinue
    
    if (-not $hasDockerComposeV2) {
        Write-Host "❌ Docker Compose未安装" -ForegroundColor Red
        exit 1
    } else {
        $env:DOCKER_COMPOSE_CMD = "docker compose"
    }
} else {
    $env:DOCKER_COMPOSE_CMD = "docker-compose"
}

# 检查数据库连接（如果配置了）
if ($env:DATABASE_URL -and $env:DATABASE_URL -match "postgresql://") {
    $dbHost = ""
    $dbPort = ""
    if ($env:DATABASE_URL -match "@([^:]+):(\d+)") {
        $dbHost = $matches[1]
        $dbPort = $matches[2]
    }
    if ($dbHost -and $dbPort) {
        Write-Host "检查PostgreSQL连接 ($dbHost:$dbPort)..." -ForegroundColor Cyan
        # 使用Test-NetConnection检查端口（Windows）
        $tcpTest = Test-NetConnection -ComputerName $dbHost -Port $dbPort -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
        if ($tcpTest.TcpTestSucceeded) {
            Write-Host "✅ PostgreSQL可访问 ($dbHost:$dbPort)" -ForegroundColor Green
        } else {
            Write-Host "⚠️  PostgreSQL不可访问 ($dbHost:$dbPort)" -ForegroundColor Yellow
        }
    }
}

# 检查Redis连接（如果配置了）
if ($env:REDIS_URL -and $env:REDIS_URL -match "redis://") {
    $redisHost = ""
    $redisPort = ""
    if ($env:REDIS_URL -match "@([^:]+):(\d+)") {
        $redisHost = $matches[1]
        $redisPort = $matches[2]
    }
    if ($redisHost -and $redisPort) {
        Write-Host "检查Redis连接 ($redisHost:$redisPort)..." -ForegroundColor Cyan
        $tcpTest = Test-NetConnection -ComputerName $redisHost -Port $redisPort -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
        if ($tcpTest.TcpTestSucceeded) {
            Write-Host "✅ Redis可访问 ($redisHost:$redisPort)" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Redis不可访问 ($redisHost:$redisPort)" -ForegroundColor Yellow
        }
    }
}

Write-Host ""

# 确认启动
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "准备启动生产服务" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "  环境: $env:ENVIRONMENT"
Write-Host "  Workers: $($env:GUNICORN_WORKERS -replace '^$', '4')"
Write-Host "  端口: $($env:API_PORT -replace '^$', '8000')"
Write-Host "  日志: logs/"
Write-Host ""
$confirm = Read-Host "确认启动？(y/n)"
if ($confirm -notmatch "^[yY]") {
    Write-Host "已取消" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "✅ 启动生产服务..." -ForegroundColor Green
Write-Host "   访问地址: http://localhost:$($env:API_PORT -replace '^$', '8000')" -ForegroundColor Cyan
Write-Host "   API文档: http://localhost:$($env:API_PORT -replace '^$', '8000')/docs" -ForegroundColor Cyan
Write-Host "   健康检查: http://localhost:$($env:API_PORT -replace '^$', '8000')/api/v1/monitoring/health" -ForegroundColor Cyan
Write-Host "   按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

# 自动初始化/迁移数据库（在Docker容器中）
Write-Host "🔄 检查数据库结构..." -ForegroundColor Cyan
$initDbOut = Join-Path $env:TEMP "init_db_out_$PID.txt"
$initDbErr = Join-Path $env:TEMP "init_db_err_$PID.txt"
$initDbProcess = Start-Process -FilePath "python" -ArgumentList "scripts/init_database.py" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $initDbOut -RedirectStandardError $initDbErr
if ($initDbProcess.ExitCode -eq 0) {
    Write-Host "✅ 数据库检查完成" -ForegroundColor Green
} else {
    Write-Host "⚠️  数据库初始化警告 (非致命错误，可能是连接问题或数据已存在)" -ForegroundColor Yellow
    if (Test-Path $initDbErr) {
        $errorContent = Get-Content $initDbErr -ErrorAction SilentlyContinue
        if ($errorContent) {
            Write-Host "错误详情: $($errorContent -join "`n")" -ForegroundColor Yellow
        }
    }
}
Remove-Item $initDbOut -ErrorAction SilentlyContinue
Remove-Item $initDbErr -ErrorAction SilentlyContinue
Write-Host ""

# 检查并清理端口占用
Write-Host "检查端口占用..." -ForegroundColor Cyan
$PORT = if ($env:API_PORT) { $env:API_PORT } else { "8000" }

# 使用 netstat 检查端口占用（Windows）
$portCheckOut = Join-Path $env:TEMP "port_check_out_$PID.txt"
$portCheckErr = Join-Path $env:TEMP "port_check_err_$PID.txt"
$netstatProcess = Start-Process -FilePath "netstat" -ArgumentList "-ano" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $portCheckOut -RedirectStandardError $portCheckErr
$portInUse = $false
if (Test-Path $portCheckOut) {
    $netstatOutput = Get-Content $portCheckOut -ErrorAction SilentlyContinue
    $portInUse = ($netstatOutput | Select-String -Pattern ":$PORT\s" | Measure-Object | Select-Object -ExpandProperty Count) -gt 0
}
Remove-Item $portCheckOut -ErrorAction SilentlyContinue
Remove-Item $portCheckErr -ErrorAction SilentlyContinue

if ($portInUse) {
    Write-Host "⚠️  端口 $PORT 已被占用，正在停止占用进程..." -ForegroundColor Yellow
    
    # 获取占用端口的进程ID
    $netstatProcess2 = Start-Process -FilePath "netstat" -ArgumentList "-ano" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $portCheckOut -RedirectStandardError $portCheckErr
    if (Test-Path $portCheckOut) {
        $netstatOutput2 = Get-Content $portCheckOut -ErrorAction SilentlyContinue
        $portLines = $netstatOutput2 | Select-String -Pattern ":$PORT\s"
        foreach ($line in $portLines) {
            # 提取进程ID（最后一列）
            if ($line -match '\s+(\d+)\s*$') {
                $processId = $matches[1]
                try {
                    Write-Host "停止进程 PID: $processId" -ForegroundColor Yellow
                    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                } catch {
                    Write-Host "无法停止进程 $processId : $_" -ForegroundColor Yellow
                }
            }
        }
    }
    Remove-Item $portCheckOut -ErrorAction SilentlyContinue
    Remove-Item $portCheckErr -ErrorAction SilentlyContinue
    
    # 等待进程停止
    Start-Sleep -Seconds 2
    
    # 再次检查端口
    $netstatProcess3 = Start-Process -FilePath "netstat" -ArgumentList "-ano" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $portCheckOut -RedirectStandardError $portCheckErr
    $portStillInUse = $false
    if (Test-Path $portCheckOut) {
        $netstatOutput3 = Get-Content $portCheckOut -ErrorAction SilentlyContinue
        $portStillInUse = ($netstatOutput3 | Select-String -Pattern ":$PORT\s" | Measure-Object | Select-Object -ExpandProperty Count) -gt 0
    }
    Remove-Item $portCheckOut -ErrorAction SilentlyContinue
    Remove-Item $portCheckErr -ErrorAction SilentlyContinue
    
    if ($portStillInUse) {
        Write-Host "❌ 无法停止占用端口 $PORT 的进程，请手动处理" -ForegroundColor Red
        Write-Host "提示: 可以使用以下命令查看占用端口的进程:" -ForegroundColor Yellow
        Write-Host "  netstat -ano | findstr :$PORT" -ForegroundColor Cyan
        exit 1
    } else {
        Write-Host "✅ 端口 $PORT 已释放" -ForegroundColor Green
    }
} else {
    Write-Host "✅ 端口 $PORT 可用" -ForegroundColor Green
}
Write-Host ""

# 启动服务（使用Docker Compose）
Write-Host "启动Docker Compose服务..." -ForegroundColor Cyan

# 检查是否存在 Windows 专用配置文件
$composeFile = if (Test-Path "docker-compose.prod.windows.yml") {
    "docker-compose.prod.windows.yml"
} else {
    "docker-compose.prod.yml"
}

Write-Host "使用配置文件: $composeFile" -ForegroundColor Cyan

if ($env:DOCKER_COMPOSE_CMD -eq "docker compose") {
    # Docker Compose V2
    docker compose -f $composeFile up -d
} else {
    # Docker Compose V1
    docker-compose -f $composeFile up -d
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 服务启动失败" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ 生产服务已启动" -ForegroundColor Green
Write-Host ""
Write-Host "查看服务状态:" -ForegroundColor Cyan
if ($env:DOCKER_COMPOSE_CMD -eq "docker compose") {
    docker compose -f $composeFile ps
} else {
    docker-compose -f $composeFile ps
}
Write-Host ""
Write-Host "查看日志:" -ForegroundColor Cyan
if ($env:DOCKER_COMPOSE_CMD -eq "docker compose") {
    Write-Host "  docker compose -f $composeFile logs -f api" -ForegroundColor Yellow
} else {
    Write-Host "  docker-compose -f $composeFile logs -f api" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "停止服务:" -ForegroundColor Cyan
if ($env:DOCKER_COMPOSE_CMD -eq "docker compose") {
    Write-Host "  docker compose -f $composeFile down" -ForegroundColor Yellow
} else {
    Write-Host "  docker-compose -f $composeFile down" -ForegroundColor Yellow
}
Write-Host ""

