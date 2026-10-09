@echo off
setlocal enabledelayedexpansion

echo ========================================
echo MySlides Application Launcher
echo ========================================
echo.

REM Get the directory where this bat file is located
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

REM Check Python installation
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)
python --version
echo.

REM Check Node.js installation
echo [2/5] Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
node --version
echo.

REM Check and install Python dependencies
echo [3/5] Checking Python dependencies...
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Python dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install Python dependencies
        pause
        exit /b 1
    )
    echo Python dependencies installed successfully.
) else (
    echo Python dependencies already installed.
)
echo.

REM Check and install frontend dependencies
echo [4/5] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    npm.cmd install
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install frontend dependencies
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo Frontend dependencies installed successfully.
) else (
    echo Frontend dependencies already installed.
)
echo.

REM Launch the application
echo [5/5] Launching MySlides application...
echo.
echo Starting backend API server...
start "MySlides Backend" cmd /k "cd /d %APP_DIR% && set PYTHONPATH=src && python -m uvicorn myslides.api.main:app --host 0.0.0.0 --port 8000 --reload"

echo Waiting for backend to start...
timeout /t 3 /nobreak >nul

echo Starting frontend development server...
start "MySlides Frontend" cmd /k "cd /d %APP_DIR%frontend && npm.cmd run dev"

echo Waiting for frontend to start...
timeout /t 5 /nobreak >nul

echo Opening browser...
start http://localhost:5173

echo.
echo ========================================
echo MySlides is launching!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo ========================================
echo.
echo Press any key to close this window (servers will continue running)...
pause >nul
