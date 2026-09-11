@echo off
setlocal
cd /d "%~dp0"
title MySlides AI Studio

echo Starting MySlides AI Server...
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
start "" http://localhost:8000
python -m uvicorn myslides.web.app:create_app --host 127.0.0.1 --port 8000 --factory
pause
