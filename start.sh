#!/bin/bash
# ============================================
# QR Platform - Start All Services
# ============================================
# Usage: chmod +x start.sh && ./start.sh
# ============================================

set -e

# Load nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

echo "========================================"
echo "  Starting QR Platform Services..."
echo "========================================"

# 0. Check Docker is running
echo ""
echo "[0/5] Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "  ERROR: Docker is not running! Start Docker first."
    exit 1
fi
echo "  Docker is running."

# 1. Setup Python virtual environment if not exists
echo ""
echo "[1/5] Setting up Python environment..."
if [ ! -d ".venv" ]; then
    echo "  Creating Python virtual environment..."
    python3 -m venv .venv
    echo "  Installing Python dependencies..."
    .venv/bin/pip install -r requirements.txt
else
    echo "  Python virtual environment already exists."
fi

# 2. Setup Frontend dependencies if not exists
echo ""
echo "[2/5] Setting up Frontend dependencies..."
if [ ! -d "frontend/node_modules" ]; then
    echo "  Installing Frontend dependencies..."
    cd frontend
    npm install
    cd ..
else
    echo "  Frontend dependencies already installed."
fi

# 3. Skip Docker containers (Supabase provides PostgreSQL)
echo ""
echo "[3/5] Skipping Docker containers (Supabase provides PostgreSQL)..."

# 4. Start Supabase local
echo ""
echo "[4/5] Starting Supabase local..."

# Check if Supabase is already running
if supabase status > /dev/null 2>&1; then
    echo "  Supabase is already running."
else
    echo "  Starting Supabase (this may take a minute)..."
    supabase start
fi

# 5. Start Backend and Frontend
echo ""
echo "[5/5] Starting Backend and Frontend..."

# Create logs directory
mkdir -p logs

# Start Backend in background
echo "  Starting Backend (FastAPI) on port 8021..."
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8021 --reload > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# Wait a bit for backend to start
sleep 3

# Start Frontend in background
echo "  Starting Frontend (Vite) on port 5173..."
cd frontend
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "  Frontend PID: $FRONTEND_PID"

# Save PIDs to file
echo $BACKEND_PID > logs/backend.pid
echo $FRONTEND_PID > logs/frontend.pid

echo ""
echo "========================================"
echo "  All services started!"
echo "========================================"
echo ""
echo "  Frontend:  http://localhost:5173"
echo "  Backend:   http://localhost:8021"
echo "  API Docs:  http://localhost:8021/docs"
echo "  Supabase:  $(supabase status | grep 'API URL' | awk '{print $3}')"
echo "  Supabase Studio: $(supabase status | grep 'Studio URL' | awk '{print $3}')"
echo "  DB:        localhost:5434"
echo ""
echo "  Backend logs:  logs/backend.log"
echo "  Frontend logs: logs/frontend.log"
echo ""
echo "  To stop all services, run: ./stop.sh"
echo ""
