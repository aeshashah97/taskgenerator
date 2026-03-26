#!/bin/bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "Restarting SOW Task Generator..."
bash "$ROOT/stop.sh"
sleep 1
bash "$ROOT/start.sh"
