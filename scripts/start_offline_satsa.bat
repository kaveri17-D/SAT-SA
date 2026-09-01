@echo off
REM SAT-SA Offline Air-Gapped Unified Platform Launcher
echo ================================================================
echo SAT-SA -- Smart Assessment Tool for Security Analytics
echo Mode: STRICT_LOCAL_ONLY (Air-Gapped Offline Production)
echo ================================================================

cd /d "%~dp0\.."

set STRICT_LOCAL_ONLY=1
set IS_AIRGAPPED=1
set ENVIRONMENT=production

if exist "backend\.venv\Scripts\python.exe" (
    set PYTHON_CMD=backend\.venv\Scripts\python.exe
) else (
    set PYTHON_CMD=python
)

echo [*] Verifying frontend static distribution...
if not exist "frontend\dist\index.html" (
    echo [!] Warning: frontend\dist\index.html not found.
    echo [*] Building frontend bundle offline...
    cd frontend && call npm.cmd run build && cd ..
)

echo [*] Starting unified SAT-SA server on http://127.0.0.1:8000 ...
"%PYTHON_CMD%" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
