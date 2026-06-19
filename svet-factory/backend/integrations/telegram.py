"""Выгрузка готового ролика в Telegram-канал (бесплатное хранилище).

Нужны TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID. Без них — пропускаем (демо).
"""
import requests

from .. import config

TIMEOUT = 180


def send_video(path: str, caption: str = "") -> str | None:
    """Шлёт видео в канал/чат. Возвращает ссылку на сообщение или None."""
    if not config.HAS_TELEGRAM:
        return None
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendVideo"
    try:
        with open(path, "rb") as f:
            r = requests.post(
                url,
                data={"chat_id": config.TELEGRAM_CHAT_ID, "caption": caption[:1024]},
                files={"video": f},
                timeout=TIMEOUT,
            )
        r.raise_for_status()
        msg = r.json().get("result", {})
        chat = msg.get("chat", {})
        mid = msg.get("message_id")
        uname = chat.get("username")
        if uname and mid:
            return f"https://t.me/{uname}/{mid}"
        return "uploaded"
    except Exception as e:  # noqa: BLE001
        print(f"[telegram] send error: {e}", flush=True)
        return None
