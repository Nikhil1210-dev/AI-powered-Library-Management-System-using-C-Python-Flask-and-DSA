@echo off
REM ============================================================
REM  LibraryPro — Windows CMD Setup (for Command Prompt users)
REM  Double-click this file OR run: setup_windows.bat
REM ============================================================

echo.
echo ========================================
echo   LibraryPro Windows Setup
echo ========================================
echo.

REM ── Compile C++ ──
echo [1/4] Compiling C++ engine...
cd backend
g++ -O2 -std=c++17 library.cpp -o library.exe
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] g++ compilation failed.
    echo Install MinGW-w64 from: https://winlibs.com
    pause
    exit /b 1
)
echo [OK] Compiled: backend\library.exe
cd ..

REM ── Virtual env ──
echo.
echo [2/4] Setting up Python virtual environment...
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate.bat
echo [OK] Virtual environment ready

REM ── Install packages ──
echo.
echo [3/4] Installing Python packages...
pip install -r requirements.txt --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
)
echo [OK] Packages installed

REM ── .env file ──
echo.
echo [4/4] Setting up .env...
if not exist .env (
    copy .env.example .env
    echo [OK] .env created - EDIT IT with your MySQL password!
) else (
    echo [OK] .env already exists
)

echo.
echo ========================================
echo   Setup complete!
echo ========================================
echo.
echo   Edit .env with your MySQL password, then:
echo.
echo   Step 1: Setup database
echo     mysql -u root -p ^< database\schema.sql
echo.
echo   Step 2: Run the app
echo     cd backend
echo     python app.py
echo.
echo   Step 3: Open browser
echo     http://localhost:5000
echo     Login: admin / admin@123
echo.
pause
