#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# подхватываем .env, если есть
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

# зависимости: ставим автоматически, если uvicorn ещё не установлен
if ! python3 -c "import uvicorn" 2>/dev/null; then
  echo "📦 Ставлю зависимости (первый запуск)…"
  pip3 install -r requirements.txt --break-system-packages 2>/dev/null \
    || pip3 install -r requirements.txt
fi

mkdir -p output .state/jobs

echo "🏭 СВЕТ — фабрика видео: http://0.0.0.0:${PORT:-8000}"
exec python3 -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
