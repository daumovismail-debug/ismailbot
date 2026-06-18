#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# подхватываем .env, если есть
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

echo "🏭 СВЕТ — фабрика видео запускается на http://localhost:${PORT:-8000}"
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
