@echo off
setlocal
cd /d "%~dp0"
title MySlides AI Studio

echo ===================================================
echo           Starting MySlides AI Studio
echo ===================================================
echo.

:: Add src directory to PYTHONPATH so Python finds the myslides package
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

:: Check and install Python dependencies
echo Checking Python dependencies...
python -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo Installing Python dependencies...
    pip install -e .
    if errorlevel 1 (
        echo Failed to install Python dependencies. Please check your Python installation.
        pause
        exit /b 1
    )
) else (
    echo Python dependencies already installed.
)

:: Check and build frontend
echo Checking frontend build...
if not exist "frontend\dist" (
    echo Installing frontend dependencies...
    npm.cmd --prefix frontend install
    if errorlevel 1 (
        echo Failed to install frontend dependencies. Please check your Node.js installation.
        pause
        exit /b 1
    )
    
    echo Building frontend...
    npm.cmd --prefix frontend run build
    if errorlevel 1 (
        echo Failed to build frontend.
        pause
        exit /b 1
    )
) else (
    echo Frontend already built.
)

echo Opening browser at http://localhost:8000 ...
start "" "http://localhost:8000"

echo Starting FastAPI / Uvicorn server...
python -m uvicorn myslides.web.app:create_app --host 127.0.0.1 --port 8000 --factory

pause
