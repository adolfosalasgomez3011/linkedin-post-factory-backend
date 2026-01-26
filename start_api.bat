@echo off
REM Start FastAPI server for Post Factory

echo Starting LinkedIn Post Factory API...
echo.
echo API will be available at:
echo   - http://localhost:8000
echo   - Interactive docs: http://localhost:8000/docs
echo   - ReDoc: http://localhost:8000/redoc
echo.

cd /d "%~dp0"
..\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

pause
