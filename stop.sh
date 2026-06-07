#!/bin/bash
# ============================================
# QR Platform - Stop All Services
# ============================================
# Usage: chmod +x stop.sh && ./stop.sh
# ============================================

echo "========================================"
echo "  Stopping QR Platform Services..."
echo "========================================"

# Stop Backend and Frontend if running
echo ""
echo "[1/3] Stopping Backend and Frontend..."

if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "  Stopping Backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
    fi
    rm logs/backend.pid
fi

if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "  Stopping Frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
    fi
    rm logs/frontend.pid
fi

# Stop Supabase
echo ""
echo "[2/3] Stopping Supabase..."
if command -v supabase &> /dev/null; then
    if supabase status > /dev/null 2>&1; then
        supabase stop
        echo "  Supabase stopped."
    else
        echo "  Supabase is not running."
    fi
fi

# Stop Docker containers
echo ""
echo "[3/3] Stopping Docker containers..."
docker compose down

echo ""
echo "========================================"
echo "  All services stopped!"
echo "========================================"
