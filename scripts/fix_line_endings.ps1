# PowerShell script: Fix Windows line endings (CRLF) to Unix line endings (LF)
# Fix Windows line endings (CRLF) to Unix line endings (LF)

$ErrorActionPreference = "Stop"

$scripts = @(
    "scripts/generate_production_config.sh",
    "scripts/prepare_minimal_deploy.sh",
    "scripts/start_prod_wsl.sh",
    "scripts/fix_line_endings.sh"
)

Write-Host "Fixing script file line endings..." -ForegroundColor Cyan
Write-Host ""

foreach ($script in $scripts) {
    if (Test-Path $script) {
        # Read file content
        $content = Get-Content $script -Raw
        
        # Replace CRLF with LF
        $content = $content -replace "`r`n", "`n"
        
        # Write back file (UTF-8 without BOM)
        [System.IO.File]::WriteAllText((Resolve-Path $script), $content, [System.Text.UTF8Encoding]::new($false))
        
        Write-Host "Fixed: $script" -ForegroundColor Green
    } else {
        Write-Host "Warning: File not found: $script" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green

