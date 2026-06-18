"""Обёртка над ElevenLabs TTS. Возвращает mp3-байты или None (демо-режим)."""
import requests

from .. import config

TIMEOUT = 120


def tts(text: str) -> bytes | None:
    """Озвучка текста голосом ElevenLabs."""
    if not config.HAS_ELEVENLABS:
        return None
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
    try:
        r = requests.post(
            url,
            headers={
                "xi-api-key": config.ELEVENLABS_API_KEY,
                "accept": "audio/mpeg",
                "content-type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.content
    except Exception as e:  # noqa: BLE001
        print(f"[elevenlabs] tts error: {e}", flush=True)
        return None
