# ============================================
# QR Platform - Diagnostics
# ============================================

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  QR Platform - Diagnostics" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. Check Docker
Write-Host "[1/5] Docker..." -ForegroundColor Yellow -NoNewline
try {
    $dockerStatus = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK" -ForegroundColor Green
    } else {
        Write-Host " NOT RUNNING!" -ForegroundColor Red
        Write-Host "  -> Start Docker Desktop first" -ForegroundColor Red
    }
} catch {
    Write-Host " NOT FOUND!" -ForegroundColor Red
    Write-Host "  -> Install Docker Desktop" -ForegroundColor Red
}

# 2. Check Supabase
Write-Host "[2/5] Supabase..." -ForegroundColor Yellow -NoNewline
try {
    $supStatus = supabase status 2>&1
    if ($supStatus -match "API URL") {
        Write-Host " OK" -ForegroundColor Green
        $supStatus | Select-String "API URL|DB URL|Studio URL" | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    } else {
        Write-Host " NOT RUNNING!" -ForegroundColor Red
        Write-Host "  -> Run: cd d:\QR && supabase start" -ForegroundColor Yellow
    }
} catch {
    Write-Host " NOT FOUND!" -ForegroundColor Red
    Write-Host "  -> Install Supabase CLI: scoop install supabase" -ForegroundColor Yellow
}

# 3. Check port 5434 (Supabase DB)
Write-Host "[3/5] Database (port 5434)..." -ForegroundColor Yellow -NoNewline
$db = Test-NetConnection -ComputerName localhost -Port 5434 -WarningAction SilentlyContinue
if ($db.TcpTestSucceeded) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " NOT REACHABLE!" -ForegroundColor Red
    Write-Host "  -> Supabase DB is not running on port 5434" -ForegroundColor Red
}

# 4. Check port 8020 (Backend)
Write-Host "[4/5] Backend (port 8020)..." -ForegroundColor Yellow -NoNewline
$backend = Test-NetConnection -ComputerName localhost -Port 8020 -WarningAction SilentlyContinue
if ($backend.TcpTestSucceeded) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " NOT REACHABLE!" -ForegroundColor Red
    Write-Host "  -> Run: cd d:\QR && python -m uvicorn app.main:app --host 0.0.0.0 --port 8020 --reload" -ForegroundColor Yellow
}

# 5. Check port 5173 (Frontend)
Write-Host "[5/5] Frontend (port 5173)..." -ForegroundColor Yellow -NoNewline
$frontend = Test-NetConnection -ComputerName localhost -Port 5173 -WarningAction SilentlyContinue
if ($frontend.TcpTestSucceeded) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " NOT REACHABLE!" -ForegroundColor Red
    Write-Host "  -> Run: cd d:\QR\frontend && npm run dev" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Diagnostics Complete" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
