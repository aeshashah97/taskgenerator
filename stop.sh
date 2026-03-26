#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$ROOT/.pids"

if [ ! -f "$PIDFILE" ]; then
  echo "No running processes found (no .pids file)."
  exit 0
fi

read BACKEND_PID FRONTEND_PID < "$PIDFILE"

echo "Stopping backend (PID $BACKEND_PID)..."
kill "$BACKEND_PID" 2>/dev/null && echo "Backend stopped." || echo "Backend already stopped."

echo "Stopping frontend (PID $FRONTEND_PID)..."
kill "$FRONTEND_PID" 2>/dev/null && echo "Frontend stopped." || echo "Frontend already stopped."

rm -f "$PIDFILE"
echo "Done."
