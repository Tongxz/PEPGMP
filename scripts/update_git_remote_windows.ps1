# Windows下更新Git远程仓库URL
# Update Git Remote Repository URL on Windows

param(
    [string]$OldRepoName = "Pyt",
    [string]$NewRepoName = "PEPGMP",
    [string]$GitHubUser = "Tongxz",
    [string]$InternalServer = "192.168.30.83"
)

Write-Host "🔄 更新Git远程仓库URL..." -ForegroundColor Cyan
Write-Host ""

# 检查是否在Git仓库中
if (-not (Test-Path ".git")) {
    Write-Host "❌ 错误: 当前目录不是Git仓库" -ForegroundColor Red
    exit 1
}

# 显示当前配置
Write-Host "📋 当前远程仓库配置:" -ForegroundColor Yellow
git remote -v
Write-Host ""

# 更新 origin (GitHub)
$originUrl = git remote get-url origin 2>$null
if ($originUrl) {
    if ($originUrl -match "github.com") {
        # 检测URL格式并生成新URL
        if ($originUrl -match "https://github.com") {
            $newOriginUrl = "https://github.com/${GitHubUser}/${NewRepoName}.git"
        } elseif ($originUrl -match "git@github.com") {
            $newOriginUrl = "git@github.com:${GitHubUser}/${NewRepoName}.git"
        } else {
            # 使用替换方式
            $newOriginUrl = $originUrl -replace "/${OldRepoName}\.git", "/${NewRepoName}.git"
            $newOriginUrl = $newOriginUrl -replace "/${OldRepoName}$", "/${NewRepoName}.git"
        }
        
        if ($originUrl -ne $newOriginUrl) {
            Write-Host "🔄 更新 origin:" -ForegroundColor Cyan
            Write-Host "  旧: $originUrl"
            Write-Host "  新: $newOriginUrl"
            git remote set-url origin $newOriginUrl
            Write-Host "  ✅ origin 已更新" -ForegroundColor Green
        } else {
            Write-Host "  ℹ️  origin 已是最新配置: $originUrl" -ForegroundColor Gray
        }
    }
}

Write-Host ""

# 更新 internal
$internalUrl = git remote get-url internal 2>$null
if ($internalUrl) {
    if ($internalUrl -match $InternalServer) {
        # 检测URL格式并生成新URL
        $newInternalUrl = "git@${InternalServer}:${NewRepoName}.git"
        
        if ($internalUrl -ne $newInternalUrl) {
            Write-Host "🔄 更新 internal:" -ForegroundColor Cyan
            Write-Host "  旧: $internalUrl"
            Write-Host "  新: $newInternalUrl"
            git remote set-url internal $newInternalUrl
            Write-Host "  ✅ internal 已更新" -ForegroundColor Green
        } else {
            Write-Host "  ℹ️  internal 已是最新配置: $internalUrl" -ForegroundColor Gray
        }
    }
}

Write-Host ""

# 显示更新后的配置
Write-Host "✅ 更新后的远程仓库配置:" -ForegroundColor Yellow
git remote -v
Write-Host ""

# 测试连接（可选，需要用户确认）
Write-Host "🔍 是否测试远程连接？(Y/N): " -NoNewline -ForegroundColor Cyan
$response = Read-Host
if ($response -eq "Y" -or $response -eq "y") {
    Write-Host ""
    Write-Host "测试 origin 连接..."
    $originTest = git fetch origin --dry-run 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ origin 连接正常" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  origin 连接失败，请检查:" -ForegroundColor Yellow
        Write-Host "     - 仓库是否已在平台上重命名"
        Write-Host "     - URL 是否正确"
        Write-Host "     - 认证信息是否正确"
    }
    
    if ($internalUrl) {
        Write-Host ""
        Write-Host "测试 internal 连接..."
        $internalTest = git fetch internal --dry-run 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ internal 连接正常" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  internal 连接失败，请检查:" -ForegroundColor Yellow
            Write-Host "     - 服务器地址是否正确"
            Write-Host "     - SSH 密钥是否配置"
        }
    }
}

Write-Host ""
Write-Host "🎉 更新完成！" -ForegroundColor Green
Write-Host ""
Write-Host "💡 提示:" -ForegroundColor Yellow
Write-Host "  - 如果仓库在GitHub/GitLab上尚未重命名，请先在平台上重命名"
Write-Host "  - 如果连接测试失败，请检查仓库名称和认证信息"
Write-Host "  - 团队其他成员也需要执行相同操作更新远程URL"

