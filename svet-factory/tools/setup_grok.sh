#!/usr/bin/env bash
# Подготовка сервера 1 ГБ к Grok-видео через ТВОЮ подписку.
# Делает 3 вещи: (1) добавляет swap-подкачку (чтобы браузер влез в 1 ГБ),
# (2) ставит Playwright, (3) ставит Chromium и его системные библиотеки.
# Запуск на сервере:  sudo bash svet-factory/tools/setup_grok.sh
set -e

echo "== 1/3 swap-подкачка (2 ГБ) =="
if swapon --show | grep -q /swapfile; then
  echo "  swap уже есть — пропускаю"
else
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "  swap включён ✅"
fi
free -h | grep -i swap || true

echo "== 2/3 Playwright =="
pip3 install playwright --break-system-packages 2>/dev/null || pip3 install playwright

echo "== 3/3 Chromium + системные библиотеки =="
python3 -m playwright install chromium
python3 -m playwright install-deps 2>/dev/null || true

echo
echo "Готово. Дальше:"
echo "  1) импортируй cookies grok.com:  python3 svet-factory/tools/grok_import_cookies.py cookies.json"
echo "  2) включи в .env:  USE_GROK_BROWSER=1"
echo "  3) перезапусти сервис"
