# 强制重新构建前端镜像（不使用缓存）

param(
    [string]$Version = (Get-Date -Format "yyyyMMdd-HHmm")
)

$ErrorActionPreference = "Stop"

Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "Force Rebuild Frontend Image (No Cache)" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Version: $Version" -ForegroundColor Yellow
Write-Host ""

# 删除旧镜像
Write-Host "[Step 1/4] Removing old images..." -ForegroundColor Green
try {
    docker rmi pepgmp-frontend:latest -f 2>$null
    Write-Host "  Old image removed" -ForegroundColor Gray
} catch {
    Write-Host "  No old image to remove" -ForegroundColor Gray
}
Write-Host ""

# 清理构建缓存
Write-Host "[Step 2/4] Cleaning build cache..." -ForegroundColor Green
docker builder prune -f
Write-Host ""

# 强制重新构建（不使用缓存）
Write-Host "[Step 3/4] Building frontend image (no cache)..." -ForegroundColor Green
Write-Host "  This may take 5-10 minutes..." -ForegroundColor Yellow
Write-Host ""

docker build -f Dockerfile.frontend `
    --no-cache `
    --build-arg VITE_API_BASE=/api/v1 `
    --build-arg BASE_URL=/ `
    --build-arg SKIP_TYPE_CHECK=true `
    -t "pepgmp-frontend:$Version" `
    -t "pepgmp-frontend:latest" `
    .

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[OK] Frontend image built successfully" -ForegroundColor Green
    
    # 显示镜像信息
    Write-Host ""
    Write-Host "Image info:" -ForegroundColor Cyan
    docker images pepgmp-frontend --format "  {{.Repository}}:{{.Tag}} - {{.ID}} - {{.Size}}"
    
    Write-Host ""
    Write-Host "[Step 4/4] Exporting image..." -ForegroundColor Green
    
    # 确保目录存在
    if (-not (Test-Path "docker-images")) {
        New-Item -ItemType Directory -Path "docker-images" | Out-Null
    }
    
    # 导出镜像
    $tarFile = "docker-images\pepgmp-frontend-$Version.tar"
    docker save "pepgmp-frontend:$Version" -o $tarFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Exported to: $tarFile" -ForegroundColor Gray
        $fileSize = (Get-Item $tarFile).Length / 1MB
        Write-Host "  File size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Gray
        
        Write-Host ""
        Write-Host "=========================================================================" -ForegroundColor Cyan
        Write-Host "Build and Export Completed Successfully!" -ForegroundColor Green
        Write-Host "=========================================================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Yellow
        Write-Host "  1. In WSL2, run:" -ForegroundColor White
        Write-Host "     cd /mnt/f/code/PythonCode/Pyt/docker-images" -ForegroundColor Gray
        Write-Host "     docker load -i pepgmp-frontend-$Version.tar" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  2. Verify image ID changed:" -ForegroundColor White
        Write-Host "     docker images | grep pepgmp-frontend" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  3. Redeploy:" -ForegroundColor White
        Write-Host "     cd ~/projects/Pyt" -ForegroundColor Gray
        Write-Host "     docker-compose down" -ForegroundColor Gray
        Write-Host "     rm -rf frontend/dist" -ForegroundColor Gray
        Write-Host "     sed -i 's/IMAGE_TAG=.*/IMAGE_TAG=$Version/' .env.production" -ForegroundColor Gray
        Write-Host "     docker-compose -f docker-compose.prod.yml --env-file .env.production up -d" -ForegroundColor Gray
        Write-Host ""
    } else {
        throw "Export failed"
    }
} else {
    Write-Host ""
    Write-Host "[ERROR] Frontend image build failed" -ForegroundColor Red
    exit 1
}

