#!/usr/bin/env python3
"""Импорт твоей сессии grok.com в формат Playwright (один раз).

Как получить cookies:
  1. Войди на grok.com в обычном браузере (Chrome/Edge).
  2. Поставь бесплатное расширение «Cookie-Editor».
  3. На вкладке grok.com: Cookie-Editor → Export → "Export as JSON".
  4. Вставь скопированное в файл cookies.json на сервере (nano cookies.json).
  5. Запусти:  python3 svet-factory/tools/grok_import_cookies.py cookies.json

Результат: .state/grok_state.json — его читает бот, заходя под твоей подпиской.
"""
import json
import os
import sys
from pathlib import Path

# куда сохранить (совпадает с config.GROK_STATE_FILE)
BASE_DIR = Path(__file__).resolve().parents[1]
STATE_FILE = Path(os.getenv("GROK_STATE_FILE", BASE_DIR / ".state" / "grok_state.json"))

# Cookie-Editor: sameSite -> формат Playwright
_SAMESITE = {"no_restriction": "None", "unspecified": "Lax",
             "lax": "Lax", "strict": "Strict", "none": "None", None: "Lax"}


def convert(raw: list) -> dict:
    cookies = []
    for c in raw:
        name = c.get("name")
        if not name:
            continue
        ck = {
            "name": name,
            "value": c.get("value", ""),
            "domain": c.get("domain", ".grok.com"),
            "path": c.get("path", "/"),
            "httpOnly": bool(c.get("httpOnly", False)),
            "secure": bool(c.get("secure", True)),
            "sameSite": _SAMESITE.get(str(c.get("sameSite")).lower()
                                      if c.get("sameSite") else None, "Lax"),
        }
        exp = c.get("expirationDate") or c.get("expires")
        if exp and not c.get("session"):
            ck["expires"] = int(float(exp))
        cookies.append(ck)
    return {"cookies": cookies, "origins": []}


def main() -> int:
    if len(sys.argv) < 2:
        print("Использование: python3 grok_import_cookies.py cookies.json")
        return 2
    src = Path(sys.argv[1])
    if not src.is_file():
        print(f"Не нашёл файл: {src}")
        return 1
    try:
        raw = json.loads(src.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"cookies.json повреждён (не JSON): {e}")
        return 1
    if isinstance(raw, dict) and "cookies" in raw:
        raw = raw["cookies"]
    if not isinstance(raw, list) or not raw:
        print("Ожидаю JSON-массив cookies из Cookie-Editor.")
        return 1

    state = convert(raw)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    print(f"✅ Сохранено {len(state['cookies'])} cookies → {STATE_FILE}")
    print("Теперь включи в .env:  USE_GROK_BROWSER=1  и перезапусти сервис.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
