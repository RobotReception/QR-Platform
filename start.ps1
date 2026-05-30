# ============================================
# QR Platform - Start All Services
# ============================================
# Usage: Right-click -> Run with PowerShell
#   OR: powershell -ExecutionPolicy Bypass -File d:\QR\start.ps1
# ============================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting QR Platform Services..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 0. Check Docker is running
Write-Host "`n[0/3] Checking Docker..." -ForegroundColor Yellow
try {
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: Docker is not running! Start Docker Desktop first." -ForegroundColor Red
        Write-Host "Press any key to exit..." -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        exit 1
    }
    Write-Host "  Docker is running." -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Docker not found!" -ForegroundColor Red
    exit 1
}

# 1. Start Supabase (if not already running)
Write-Host "`n[1/3] Starting Supabase..." -ForegroundColor Yellow
$supStatus = .\supabase.exe status 2>&1
if ($supStatus -match "API URL") {
    Write-Host "  Supabase is already running." -ForegroundColor Green
} else {
    Write-Host "  Starting Supabase (this may take a minute)..." -ForegroundColor Gray
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd d:\QR; Write-Host 'Starting Supabase...' -ForegroundColor Green; .\supabase.exe start; Write-Host 'Supabase started!' -ForegroundColor Green"
    # Wait for Supabase DB to be ready
    $maxWait = 90
    $waited = 0
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 3
        $waited += 3
        $check = Test-NetConnection -ComputerName localhost -Port 5434 -WarningAction SilentlyContinue
        if ($check.TcpTestSucceeded) {
            Write-Host "  Supabase DB ready (waited ${waited}s)." -ForegroundColor Green
            break
        }
        Write-Host "  Waiting for Supabase DB... (${waited}s)" -ForegroundColor Gray
    }
    if ($waited -ge $maxWait) {
        Write-Host "  WARNING: Supabase DB might not be ready yet. Proceeding anyway..." -ForegroundColor Yellow
    }
    Start-Sleep -Seconds 5
}

# 2. Start Backend (FastAPI) in a new window
Write-Host "`n[2/3] Starting Backend (FastAPI) on port 8020..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd d:\QR; Write-Host 'Backend starting...' -ForegroundColor Green; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8020 --reload"

Start-Sleep -Seconds 3

# 3. Start Frontend (Vite) in a new window
Write-Host "[3/3] Starting Frontend (Vite) on port 5173..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd d:\QR\frontend; Write-Host 'Frontend starting...' -ForegroundColor Green; npm run dev"

Start-Sleep -Seconds 3

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend:  http://localhost:5173" -ForegroundColor White
Write-Host "  Backend:   http://localhost:8020" -ForegroundColor White
Write-Host "  API Docs:  http://localhost:8020/docs" -ForegroundColor White
Write-Host "  Supabase:  http://localhost:54325 (Studio)" -ForegroundColor White
Write-Host "  DB:        localhost:5434" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
