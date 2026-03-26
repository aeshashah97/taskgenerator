#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$ROOT/.pids"

# Backend
echo "Starting backend..."
cd "$ROOT/backend"
source .venv/Scripts/activate
uvicorn main:app --reload &
BACKEND_PID=$!

# Frontend
echo "Starting frontend..."
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

# Save PIDs
echo "$BACKEND_PID $FRONTEND_PID" > "$PIDFILE"

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo ""
echo "PIDs saved ($BACKEND_PID, $FRONTEND_PID). Run ./stop.sh to stop."
