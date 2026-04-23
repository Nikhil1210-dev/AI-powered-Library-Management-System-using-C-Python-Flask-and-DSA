# ============================================================
#  LibraryPro — Windows Setup Script (PowerShell)
#  Run this from the LibraryPro\ root folder:
#    .\setup_windows.ps1
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LibraryPro — Windows Setup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── STEP 1: Compile C++ ──────────────────────────────────
Write-Host "[1/5] Compiling C++ engine..." -ForegroundColor Yellow

Set-Location backend

# Try g++ (MinGW / MSYS2)
$gpp = Get-Command g++ -ErrorAction SilentlyContinue
if ($gpp) {
    g++ -O2 -std=c++17 library.cpp -o library.exe
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      ✅ Compiled: backend\library.exe" -ForegroundColor Green
    } else {
        Write-Host "      ❌ g++ failed. Check error above." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "      ❌ g++ not found. Install MinGW-w64 first." -ForegroundColor Red
    Write-Host "         Download: https://winlibs.com" -ForegroundColor Gray
    Write-Host "         Or via MSYS2: pacman -S mingw-w64-x86_64-gcc" -ForegroundColor Gray
    exit 1
}

Set-Location ..

# ── STEP 2: Check Python ─────────────────────────────────
Write-Host ""
Write-Host "[2/5] Checking Python..." -ForegroundColor Yellow

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}

if ($python) {
    $ver = & python --version 2>&1
    Write-Host "      ✅ Found: $ver" -ForegroundColor Green
} else {
    Write-Host "      ❌ Python not found. Download: https://python.org" -ForegroundColor Red
    exit 1
}

# ── STEP 3: Create virtual environment ───────────────────
Write-Host ""
Write-Host "[3/5] Creating virtual environment..." -ForegroundColor Yellow

if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "      ✅ venv created" -ForegroundColor Green
} else {
    Write-Host "      ℹ️  venv already exists, skipping" -ForegroundColor Gray
}

# Activate venv
& ".\venv\Scripts\Activate.ps1"
Write-Host "      ✅ venv activated" -ForegroundColor Green

# ── STEP 4: Install packages ──────────────────────────────
Write-Host ""
Write-Host "[4/5] Installing Python packages..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "      ✅ Packages installed" -ForegroundColor Green
} else {
    Write-Host "      ❌ pip install failed" -ForegroundColor Red
    exit 1
}

# ── STEP 5: .env file ─────────────────────────────────────
Write-Host ""
Write-Host "[5/5] Checking .env file..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "      ✅ .env created from .env.example" -ForegroundColor Green
    Write-Host "      ⚠️  EDIT .env and add your MySQL password!" -ForegroundColor Yellow
} else {
    Write-Host "      ✅ .env already exists" -ForegroundColor Green
}

# ── DONE ──────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✅ Setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "    1. Edit .env  →  set your MySQL password" -ForegroundColor Gray
Write-Host "    2. Run MySQL schema:" -ForegroundColor Gray
Write-Host "       mysql -u root -p < database\schema.sql" -ForegroundColor Cyan
Write-Host "    3. Start the app:" -ForegroundColor Gray
Write-Host "       cd backend" -ForegroundColor Cyan
Write-Host "       python app.py" -ForegroundColor Cyan
Write-Host "    4. Open browser: http://localhost:5000" -ForegroundColor Cyan
Write-Host "       Login: admin / admin@123" -ForegroundColor Cyan
Write-Host ""
