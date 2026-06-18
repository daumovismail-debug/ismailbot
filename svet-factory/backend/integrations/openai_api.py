"""OpenAI (ChatGPT): текст для сценария/агентов и картинки (gpt-image-1).

Возвращают None при отсутствии ключа или ошибке — тогда работает демо-режим.
"""
import base64

import requests

from .. import config

TIMEOUT = 180
HAS_LLM = config.HAS_OPENAI


def _log(msg: str) -> None:
    print(f"[openai] {msg}", flush=True)


def chat(system: str, user: str) -> str | None:
    """Текстовый запрос к ChatGPT (для сценария и агентов-промптеров)."""
    if not config.HAS_OPENAI:
        return None
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            json={
                "model": config.OPENAI_TEXT_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001
        _log(f"chat error: {e}")
        return None


def generate_image(prompt: str) -> bytes | None:
    """Картинка через gpt-image-1 (вертикаль 1024x1536 — ближе всего к 9:16)."""
    if not config.HAS_OPENAI:
        return None
    try:
        r = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            json={
                "model": config.OPENAI_IMAGE_MODEL,
                "prompt": prompt,
                "size": "1024x1536",
                "n": 1,
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()["data"][0]
        if data.get("b64_json"):
            return base64.b64decode(data["b64_json"])
        if data.get("url"):
            img = requests.get(data["url"], timeout=TIMEOUT)
            img.raise_for_status()
            return img.content
        _log("image: no data in response")
        return None
    except Exception as e:  # noqa: BLE001
        _log(f"image error: {e}")
        return None
