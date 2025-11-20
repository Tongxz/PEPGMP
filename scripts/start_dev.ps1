# 开发环境启动脚本 (PowerShell版本)
# Development Environment Startup Script (PowerShell Version)

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

Write-Host "=== 启动开发环境 ===" -ForegroundColor Cyan
Write-Host ""

# 检查虚拟环境
if (-not (Test-Path "venv")) {
    Write-Host "虚拟环境不存在，请先运行: python -m venv venv" -ForegroundColor Red
    exit 1
}

# 激活虚拟环境
Write-Host "激活虚拟环境..." -ForegroundColor Green
$venvActivateScript = Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"
$venvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"

if (Test-Path $venvActivateScript) {
    # 激活虚拟环境
    & $venvActivateScript
    # 确保使用虚拟环境中的Python
    $venvScriptsPath = Join-Path $ProjectRoot "venv\Scripts"
    $env:Path = $venvScriptsPath + ";" + $env:Path
} elseif (Test-Path $venvPython) {
    # 如果激活脚本不存在但Python存在，直接使用虚拟环境的Python
    Write-Host "虚拟环境激活脚本不存在，直接使用虚拟环境Python" -ForegroundColor Yellow
    $venvScriptsPath = Join-Path $ProjectRoot "venv\Scripts"
    $env:Path = $venvScriptsPath + ";" + $env:Path
} else {
    Write-Host "虚拟环境不存在或不完整: $venvActivateScript" -ForegroundColor Red
    exit 1
}

# 验证Python是否来自虚拟环境
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $pythonPath = $pythonCmd.Source
    if ($pythonPath -and $pythonPath -like "*venv*") {
        Write-Host "使用虚拟环境Python: $pythonPath" -ForegroundColor Green
    } else {
        Write-Host "警告: 可能未使用虚拟环境Python" -ForegroundColor Yellow
    }
}

# 检查.env文件
if (-not (Test-Path ".env")) {
    Write-Host ".env文件不存在，从.env.example复制..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "已创建.env文件" -ForegroundColor Green
        Write-Host "请根据需要修改配置（特别是数据库和Redis密码）" -ForegroundColor Yellow
        Write-Host ""
        $editEnv = Read-Host "是否现在编辑.env文件？(y/n)"
        if ($editEnv -match "^[yY]") {
            # 尝试使用默认编辑器
            $editor = $env:EDITOR
            if (-not $editor) {
                # Windows 默认使用 notepad
                $editor = "notepad"
            }
            Start-Process $editor ".env"
            Write-Host "请在编辑器中修改配置后按任意键继续..." -ForegroundColor Yellow
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
    } else {
        Write-Host ".env.example文件不存在" -ForegroundColor Red
        exit 1
    }
}

# 检查python-dotenv
Write-Host ""
Write-Host "检查依赖..." -ForegroundColor Cyan
$dotenvInstalled = $false

# 使用临时文件来检查模块，避免PowerShell捕获错误
$tempScript = Join-Path $env:TEMP "check_dotenv_$PID.py"
try {
    # 创建临时Python脚本
    @"
import sys
try:
    import dotenv
    sys.exit(0)
except ImportError:
    sys.exit(1)
"@ | Out-File -FilePath $tempScript -Encoding UTF8 -Force
    
    # 执行检查，完全抑制输出
    $process = Start-Process -FilePath "python" -ArgumentList $tempScript -NoNewWindow -Wait -PassThru -RedirectStandardOutput "NUL" -RedirectStandardError "NUL"
    if ($process.ExitCode -eq 0) {
        $dotenvInstalled = $true
    }
} catch {
    # 如果上面的方法失败，尝试直接检查
    $dotenvInstalled = $false
} finally {
    # 清理临时文件
    if (Test-Path $tempScript) {
        Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
    }
}

if (-not $dotenvInstalled) {
    Write-Host "python-dotenv未安装" -ForegroundColor Yellow
    $installDotenv = Read-Host "是否现在安装？(y/n)"
    if ($installDotenv -match "^[yY]") {
        $installProcess = Start-Process -FilePath "python" -ArgumentList "-m", "pip", "install", "python-dotenv" -NoNewWindow -Wait -PassThru
        if ($installProcess.ExitCode -ne 0) {
            Write-Host "python-dotenv安装失败" -ForegroundColor Red
            exit 1
        }
        Write-Host "python-dotenv安装成功" -ForegroundColor Green
    } else {
        Write-Host "警告: 未安装python-dotenv，将仅使用环境变量" -ForegroundColor Yellow
    }
} else {
    Write-Host "python-dotenv已安装" -ForegroundColor Green
}

# 检查并启动Docker服务
Write-Host ""
Write-Host "检查依赖服务..." -ForegroundColor Cyan

# 检查Docker是否安装
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    # 检查Docker是否正在运行（使用Start-Process避免PowerShell捕获错误）
    $nullOut = Join-Path $env:TEMP "docker_out_$PID.txt"
    $nullErr = Join-Path $env:TEMP "docker_err_$PID.txt"
    $dockerInfoProcess = Start-Process -FilePath "docker" -ArgumentList "info" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $nullOut -RedirectStandardError $nullErr
    $dockerRunning = ($dockerInfoProcess.ExitCode -eq 0)
    # 清理临时文件
    Remove-Item $nullOut -ErrorAction SilentlyContinue
    Remove-Item $nullErr -ErrorAction SilentlyContinue
    
    if (-not $dockerRunning) {
        Write-Host "Docker未运行，请启动Docker Desktop" -ForegroundColor Yellow
        Write-Host "等待Docker启动..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        
        $nullOut = Join-Path $env:TEMP "docker_out_$PID.txt"
        $nullErr = Join-Path $env:TEMP "docker_err_$PID.txt"
        $dockerInfoProcess = Start-Process -FilePath "docker" -ArgumentList "info" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $nullOut -RedirectStandardError $nullErr
        $dockerRunning = ($dockerInfoProcess.ExitCode -eq 0)
        # 清理临时文件
        Remove-Item $nullOut -ErrorAction SilentlyContinue
        Remove-Item $nullErr -ErrorAction SilentlyContinue
        
        if (-not $dockerRunning) {
            Write-Host "Docker仍未就绪，请手动启动Docker Desktop后重试" -ForegroundColor Red
            Write-Host "提示: 如果不需要Docker服务，可以跳过此步骤继续运行" -ForegroundColor Yellow
            $continue = Read-Host "是否继续启动后端服务（跳过Docker）？(y/n)"
            if ($continue -notmatch "^[yY]") {
                exit 1
            }
        }
    }

    if ($dockerRunning) {
        # 检查并启动PostgreSQL
        $postgresOut = Join-Path $env:TEMP "postgres_out_$PID.txt"
        $postgresErr = Join-Path $env:TEMP "postgres_err_$PID.txt"
        $postgresProcess = Start-Process -FilePath "docker" -ArgumentList "ps", "--format", "{{.Names}}" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $postgresOut -RedirectStandardError $postgresErr
        $postgresOutput = ""
        if ($postgresProcess.ExitCode -eq 0 -and (Test-Path $postgresOut)) {
            $postgresOutput = Get-Content $postgresOut -ErrorAction SilentlyContinue
        }
        Remove-Item $postgresOut -ErrorAction SilentlyContinue
        Remove-Item $postgresErr -ErrorAction SilentlyContinue
        $postgresRunning = $postgresOutput | Select-String -Pattern "pyt-postgres-dev"
        
        if (-not $postgresRunning) {
            Write-Host "PostgreSQL服务未运行，正在启动..." -ForegroundColor Yellow
            $composeOut = Join-Path $env:TEMP "compose_out_$PID.txt"
            $composeErr = Join-Path $env:TEMP "compose_err_$PID.txt"
            $composeProcess = Start-Process -FilePath "docker-compose" -ArgumentList "up", "-d", "database" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $composeOut -RedirectStandardError $composeErr
            Remove-Item $composeOut -ErrorAction SilentlyContinue
            Remove-Item $composeErr -ErrorAction SilentlyContinue
            if ($composeProcess.ExitCode -ne 0) {
                Write-Host "Docker Compose启动失败，请检查docker-compose.yml配置" -ForegroundColor Red
                exit 1
            }
            Write-Host "等待PostgreSQL启动..." -ForegroundColor Yellow
            Start-Sleep -Seconds 8
            
            $postgresOut = Join-Path $env:TEMP "postgres_out_$PID.txt"
            $postgresErr = Join-Path $env:TEMP "postgres_err_$PID.txt"
            $postgresProcess = Start-Process -FilePath "docker" -ArgumentList "ps", "--format", "{{.Names}}" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $postgresOut -RedirectStandardError $postgresErr
            if ($postgresProcess.ExitCode -eq 0 -and (Test-Path $postgresOut)) {
                $postgresOutput = Get-Content $postgresOut -ErrorAction SilentlyContinue
            }
            Remove-Item $postgresOut -ErrorAction SilentlyContinue
            Remove-Item $postgresErr -ErrorAction SilentlyContinue
            $postgresRunning = $postgresOutput | Select-String -Pattern "pyt-postgres-dev"
            if ($postgresRunning) {
                Write-Host "PostgreSQL服务已启动" -ForegroundColor Green
            } else {
                Write-Host "PostgreSQL启动失败，请检查Docker日志: docker logs pyt-postgres-dev" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "PostgreSQL服务运行中" -ForegroundColor Green
        }

        # 检查并启动Redis
        $redisOut = Join-Path $env:TEMP "redis_out_$PID.txt"
        $redisErr = Join-Path $env:TEMP "redis_err_$PID.txt"
        $redisProcess = Start-Process -FilePath "docker" -ArgumentList "ps", "--format", "{{.Names}}" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $redisOut -RedirectStandardError $redisErr
        $redisOutput = ""
        if ($redisProcess.ExitCode -eq 0 -and (Test-Path $redisOut)) {
            $redisOutput = Get-Content $redisOut -ErrorAction SilentlyContinue
        }
        Remove-Item $redisOut -ErrorAction SilentlyContinue
        Remove-Item $redisErr -ErrorAction SilentlyContinue
        $redisRunning = $redisOutput | Select-String -Pattern "pyt-redis-dev"
        
        if (-not $redisRunning) {
            Write-Host "Redis服务未运行，正在启动..." -ForegroundColor Yellow
            $composeOut = Join-Path $env:TEMP "compose_out_$PID.txt"
            $composeErr = Join-Path $env:TEMP "compose_err_$PID.txt"
            $composeProcess = Start-Process -FilePath "docker-compose" -ArgumentList "up", "-d", "redis" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $composeOut -RedirectStandardError $composeErr
            Remove-Item $composeOut -ErrorAction SilentlyContinue
            Remove-Item $composeErr -ErrorAction SilentlyContinue
            if ($composeProcess.ExitCode -ne 0) {
                Write-Host "Docker Compose启动失败，请检查docker-compose.yml配置" -ForegroundColor Red
                exit 1
            }
            Write-Host "等待Redis启动..." -ForegroundColor Yellow
            Start-Sleep -Seconds 3
            
            $redisOut = Join-Path $env:TEMP "redis_out_$PID.txt"
            $redisErr = Join-Path $env:TEMP "redis_err_$PID.txt"
            $redisProcess = Start-Process -FilePath "docker" -ArgumentList "ps", "--format", "{{.Names}}" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $redisOut -RedirectStandardError $redisErr
            if ($redisProcess.ExitCode -eq 0 -and (Test-Path $redisOut)) {
                $redisOutput = Get-Content $redisOut -ErrorAction SilentlyContinue
            }
            Remove-Item $redisOut -ErrorAction SilentlyContinue
            Remove-Item $redisErr -ErrorAction SilentlyContinue
            $redisRunning = $redisOutput | Select-String -Pattern "pyt-redis-dev"
            if ($redisRunning) {
                Write-Host "Redis服务已启动" -ForegroundColor Green
            } else {
                Write-Host "Redis启动失败，请检查Docker日志: docker logs pyt-redis-dev" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "Redis服务运行中" -ForegroundColor Green
        }
    }
} else {
    Write-Host "Docker未安装或未运行" -ForegroundColor Yellow
    Write-Host "请安装Docker Desktop或使用其他方式提供数据库服务" -ForegroundColor Yellow
}

# 检查关键依赖
Write-Host ""
Write-Host "检查关键依赖..." -ForegroundColor Cyan
$missingDeps = @()

# 检查 uvicorn
$uvicornOut = Join-Path $env:TEMP "uvicorn_check_out_$PID.txt"
$uvicornErr = Join-Path $env:TEMP "uvicorn_check_err_$PID.txt"
$uvicornCheck = Start-Process -FilePath "python" -ArgumentList "-c", "import uvicorn" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $uvicornOut -RedirectStandardError $uvicornErr
Remove-Item $uvicornOut -ErrorAction SilentlyContinue
Remove-Item $uvicornErr -ErrorAction SilentlyContinue
if ($uvicornCheck.ExitCode -ne 0) {
    $missingDeps += "uvicorn"
}

if ($missingDeps.Count -gt 0) {
    Write-Host "缺少以下依赖: $($missingDeps -join ', ')" -ForegroundColor Yellow
    Write-Host "正在安装项目依赖..." -ForegroundColor Yellow
    
    # 尝试使用 pyproject.toml 安装
    if (Test-Path "pyproject.toml") {
        Write-Host "使用 pyproject.toml 安装依赖..." -ForegroundColor Cyan
        $installProcess = Start-Process -FilePath "python" -ArgumentList "-m", "pip", "install", "-e", "." -NoNewWindow -Wait -PassThru
        if ($installProcess.ExitCode -ne 0) {
            Write-Host "依赖安装失败，请手动运行: pip install -e ." -ForegroundColor Red
            exit 1
        }
    } else {
        # 如果没有 pyproject.toml，尝试安装 requirements.txt
        if (Test-Path "requirements.txt") {
            Write-Host "使用 requirements.txt 安装依赖..." -ForegroundColor Cyan
            $installProcess = Start-Process -FilePath "python" -ArgumentList "-m", "pip", "install", "-r", "requirements.txt" -NoNewWindow -Wait -PassThru
            if ($installProcess.ExitCode -ne 0) {
                Write-Host "依赖安装失败，请手动运行: pip install -r requirements.txt" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "未找到依赖配置文件，请手动安装: pip install uvicorn fastapi" -ForegroundColor Red
            exit 1
        }
    }
    Write-Host "依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "关键依赖已安装" -ForegroundColor Green
}

# 验证配置
Write-Host ""
Write-Host "验证配置..." -ForegroundColor Cyan
try {
    python -c "from src.config.env_config import Config; Config().validate()" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "配置验证通过" -ForegroundColor Green
    } else {
        throw "Config validation failed"
    }
} catch {
    Write-Host "配置验证失败，请检查.env文件" -ForegroundColor Red
    Write-Host "错误详情: $_" -ForegroundColor Red
    exit 1
}

# 设置调试ROI保存（可选）
if (-not $env:SAVE_DEBUG_ROI) {
    $env:SAVE_DEBUG_ROI = "true"
}
if (-not $env:DEBUG_ROI_DIR) {
    $env:DEBUG_ROI_DIR = "debug/roi"
}

# 自动初始化/迁移数据库
Write-Host ""
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
Write-Host ""
Write-Host "检查端口占用..." -ForegroundColor Cyan
$PORT = 8000

# 检查端口是否被占用
$portCheckOut = Join-Path $env:TEMP "port_check_out_$PID.txt"
$portCheckErr = Join-Path $env:TEMP "port_check_err_$PID.txt"

# 使用 netstat 检查端口占用（Windows 兼容）
$netstatProcess = Start-Process -FilePath "netstat" -ArgumentList "-ano" -NoNewWindow -Wait -PassThru -RedirectStandardOutput $portCheckOut -RedirectStandardError $portCheckErr
$portInUse = $false
if (Test-Path $portCheckOut) {
    $netstatOutput = Get-Content $portCheckOut -ErrorAction SilentlyContinue
    $portInUse = $netstatOutput | Select-String -Pattern ":$PORT\s" | Measure-Object | Select-Object -ExpandProperty Count
    $portInUse = ($portInUse -gt 0)
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
            $pidMatch = $line -match '\s+(\d+)\s*$'
            if ($pidMatch) {
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
        Write-Host "netstat -ano | findstr :$PORT" -ForegroundColor Cyan
        exit 1
    } else {
        Write-Host "✅ 端口 $PORT 已释放" -ForegroundColor Green
    }
} else {
    Write-Host "✅ 端口 $PORT 可用" -ForegroundColor Green
}
Write-Host ""

# 启动后端
Write-Host ""
Write-Host "✅ 启动后端服务..." -ForegroundColor Green
Write-Host "   访问地址: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   API文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "   ROI调试保存: $env:SAVE_DEBUG_ROI (目录: $env:DEBUG_ROI_DIR)" -ForegroundColor Cyan
Write-Host "   按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

# 启动uvicorn服务器
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload --log-level info
