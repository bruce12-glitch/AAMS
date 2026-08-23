#!/usr/bin/env bash
# Start the AAMS live prototype: FastAPI :8000 + Vite console :3000
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$ROOT/fablab-face-attendance"
VENV="$API_DIR/.venv"

echo "==> AAMS live server"
echo "    repo: $ROOT"

if [ ! -d "$VENV" ]; then
  echo "==> creating Python venv"
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "==> installing API deps (no InsightFace)"
pip install -q -r "$API_DIR/requirements-api.txt"

if [ ! -f "$API_DIR/.env" ]; then
  cp "$API_DIR/.env.example" "$API_DIR/.env"
fi

echo "==> database"
cd "$API_DIR"
python -m scripts.create_db
if [ "${FORCE_SEED:-0}" = "1" ]; then
  python -m scripts.seed_demo_data --force
else
  python -m scripts.seed_demo_data --if-empty
fi

echo "==> FastAPI on 0.0.0.0:8000"
cd "$API_DIR"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

cleanup() {
  echo "==> stopping API ($API_PID)"
  kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# wait until /health answers so Vite's first proxy isn't a hard fail
for _ in $(seq 1 30); do
  if python - <<'PY'
import urllib.request
urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1)
PY
  then
    echo "==> API healthy"
    break
  fi
  sleep 0.4
done

cd "$ROOT"
if [ ! -d "$ROOT/node_modules" ]; then
  echo "==> npm install"
  npm install
fi

echo "==> Vite console on 0.0.0.0:3000 (proxies /api → :8000)"
exec npm run dev
