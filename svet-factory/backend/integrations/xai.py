"""xAI (Grok Imagine): анимация картинки в видео (image-to-video).

Эндпоинт: POST https://api.x.ai/v1/videos/generations -> request_id,
затем поллинг GET https://api.x.ai/v1/videos/{request_id} до готовности.
Картинку Grok забирает по URL, поэтому нужен публичный адрес сервиса
(config.PUBLIC_BASE_URL). Возвращает None при отсутствии ключа/ошибке (демо-режим).
"""
import time

import requests

from .. import config

TIMEOUT = 60


def _log(msg: str) -> None:
    print(f"[xai] {msg}", flush=True)


def generate_video(prompt: str, image_url: str | None = None,
                   seconds: int | None = None) -> bytes | None:
    """Оживляет кадр по его публичному URL в видео заданной длины."""
    if not config.HAS_XAI:
        return None
    body: dict = {
        "model": config.XAI_VIDEO_MODEL,
        "prompt": prompt,
        "duration": seconds or config.SCENE_SECONDS,
    }
    if image_url:
        body["image"] = {"url": image_url}
    try:
        r = requests.post(
            "https://api.x.ai/v1/videos/generations",
            headers={"Authorization": f"Bearer {config.XAI_API_KEY}"},
            json=body,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        req_id = r.json().get("request_id") or r.json().get("id")
        if not req_id:
            _log("no request_id in response")
            return None

        # поллинг готовности
        for _ in range(60):
            time.sleep(6)
            poll = requests.get(
                f"https://api.x.ai/v1/videos/{req_id}",
                headers={"Authorization": f"Bearer {config.XAI_API_KEY}"},
                timeout=TIMEOUT,
            ).json()
            status = poll.get("status")
            if status in ("completed", "succeeded", "done") or poll.get("url"):
                return _download(poll)
            if status in ("failed", "error"):
                _log(f"generation failed: {poll}")
                return None
        _log("timeout waiting for video")
        return None
    except Exception as e:  # noqa: BLE001
        _log(f"video error: {e}")
        return None


def _download(poll: dict) -> bytes | None:
    url = (poll.get("url")
           or (poll.get("video") or {}).get("url")
           or ((poll.get("data") or [{}])[0].get("url")))
    if not url:
        _log(f"no video url in: {poll}")
        return None
    try:
        dl = requests.get(url, timeout=TIMEOUT * 2)
        dl.raise_for_status()
        return dl.content
    except Exception as e:  # noqa: BLE001
        _log(f"download error: {e}")
        return None
