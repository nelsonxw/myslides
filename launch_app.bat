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

echo Opening browser at http://localhost:8000 ...
start "" "http://localhost:8000"

echo Starting FastAPI / Uvicorn server...
python -m uvicorn myslides.web.app:create_app --host 127.0.0.1 --port 8000 --factory

pause
