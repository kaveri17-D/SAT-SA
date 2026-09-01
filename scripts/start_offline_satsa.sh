#!/bin/bash
# SAT-SA Offline Air-Gapped Unified Platform Launcher
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "================================================================"
echo "SAT-SA -- Smart Assessment Tool for Security Analytics"
echo "Mode: STRICT_LOCAL_ONLY (Air-Gapped Offline Production)"
echo "================================================================"

export STRICT_LOCAL_ONLY=1
export IS_AIRGAPPED=1
export ENVIRONMENT=production

if [ -f "backend/.venv/bin/python" ]; then
    PYTHON_CMD="backend/.venv/bin/python"
else
    PYTHON_CMD="python3"
fi

if [ ! -f "frontend/dist/index.html" ]; then
    echo "[!] Building frontend bundle..."
    cd frontend && npm run build && cd ..
fi

echo "[*] Starting unified SAT-SA server on http://127.0.0.1:8000 ..."
$PYTHON_CMD -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
