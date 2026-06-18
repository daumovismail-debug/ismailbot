"""Обёртка над Google Gemini API: текст, картинки (Nano Banana Pro), видео (Veo 3.1).

Все функции возвращают None, если ключа нет или произошла ошибка, —
тогда конвейер использует плейсхолдеры (демо-режим). Так сервис всегда
доходит до готового ролика, а с ключом выдаёт настоящий контент.
"""
import base64
import time

import requests

from .. import config

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"
TIMEOUT = 120


def _log(msg: str) -> None:
    print(f"[gemini] {msg}", flush=True)


def generate_text(prompt: str) -> str | None:
    """Генерация текста (сценарий, раскадровка)."""
    if not config.HAS_GEMINI:
        return None
    url = f"{API_ROOT}/models/{config.GEMINI_TEXT_MODEL}:generateContent"
    try:
        r = requests.post(
            url,
            params={"key": config.GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:  # noqa: BLE001
        _log(f"text error: {e}")
        return None


def generate_image(prompt: str, ref_image: bytes | None = None) -> bytes | None:
    """Картинка через Nano Banana Pro. ref_image — эталон героини для консистентности."""
    if not config.HAS_GEMINI:
        return None
    url = f"{API_ROOT}/models/{config.GEMINI_IMAGE_MODEL}:generateContent"
    parts: list[dict] = [{"text": prompt}]
    if ref_image:
        parts.append({
            "inline_data": {
                "mime_type": "image/png",
                "data": base64.b64encode(ref_image).decode(),
            }
        })
    try:
        r = requests.post(
            url,
            params={"key": config.GEMINI_API_KEY},
            json={
                "contents": [{"parts": parts}],
                "generationConfig": {"responseModalities": ["IMAGE"]},
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        for part in data["candidates"][0]["content"]["parts"]:
            inline = part.get("inline_data") or part.get("inlineData")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
        _log("image: no inline data in response")
        return None
    except Exception as e:  # noqa: BLE001
        _log(f"image error: {e}")
        return None


def generate_video(prompt: str, image: bytes | None = None) -> bytes | None:
    """Видео-клип через Veo 3.1 (long-running operation + поллинг)."""
    if not config.HAS_GEMINI:
        return None
    start_url = f"{API_ROOT}/models/{config.GEMINI_VIDEO_MODEL}:predictLongRunning"
    instance: dict = {"prompt": prompt}
    if image:
        instance["image"] = {
            "bytesBase64Encoded": base64.b64encode(image).decode(),
            "mimeType": "image/png",
        }
    try:
        r = requests.post(
            start_url,
            params={"key": config.GEMINI_API_KEY},
            json={"instances": [instance]},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        op_name = r.json()["name"]

        # Поллинг операции (Veo рендерит видео не мгновенно)
        for _ in range(60):
            time.sleep(8)
            op = requests.get(
                f"{API_ROOT}/{op_name}",
                params={"key": config.GEMINI_API_KEY},
                timeout=TIMEOUT,
            ).json()
            if op.get("done"):
                return _extract_video_bytes(op)
        _log("video: timeout waiting for operation")
        return None
    except Exception as e:  # noqa: BLE001
        _log(f"video error: {e}")
        return None


def _extract_video_bytes(op: dict) -> bytes | None:
    """Достаём байты видео из ответа операции (формат у Veo может отличаться)."""
    try:
        resp = op.get("response", {})
        # пробуем разные формы ответа
        videos = (
            resp.get("generatedVideos")
            or resp.get("videos")
            or resp.get("generate_video_response", {}).get("generatedSamples")
            or []
        )
        if not videos:
            _log("video: no videos in response")
            return None
        v = videos[0]
        # вариант 1: inline base64
        b64 = (
            v.get("bytesBase64Encoded")
            or v.get("video", {}).get("bytesBase64Encoded")
        )
        if b64:
            return base64.b64decode(b64)
        # вариант 2: ссылка на файл
        uri = v.get("uri") or v.get("video", {}).get("uri")
        if uri:
            sep = "&" if "?" in uri else "?"
            dl = requests.get(f"{uri}{sep}key={config.GEMINI_API_KEY}", timeout=TIMEOUT)
            dl.raise_for_status()
            return dl.content
        _log("video: unknown response shape")
        return None
    except Exception as e:  # noqa: BLE001
        _log(f"video extract error: {e}")
        return None
