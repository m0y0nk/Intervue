#!/bin/sh
set -e

PORT="${PORT:-8000}"

echo ""
echo "=========================================================================="
echo "  🚀 Intervue AI Technical Simulator is LIVE!"
echo "  👉 Access the platform at: http://localhost:${PORT}"
echo "=========================================================================="
echo ""

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
