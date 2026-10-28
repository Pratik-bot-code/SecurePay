# SecurePay PowerShell Launcher
$rootDir = $PSScriptRoot
Set-Location -LiteralPath $rootDir

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Starting SecurePay (Backend + Frontend)              " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"

Write-Host "`n[1/2] Launching Backend API on http://127.0.0.1:8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location -LiteralPath '$backendDir'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

Start-Sleep -Seconds 2

Write-Host "[2/2] Launching Frontend Web on http://localhost:5173..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location -LiteralPath '$frontendDir'; npm run dev"

Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "   SecurePay is now running!" -ForegroundColor Green
Write-Host "   - Web Application: http://localhost:5173" -ForegroundColor White
Write-Host "   - Backend API:     http://127.0.0.1:8000" -ForegroundColor White
Write-Host "   - API Docs:        http://127.0.0.1:8000/api/docs" -ForegroundColor White
Write-Host "========================================================`n" -ForegroundColor Cyan
