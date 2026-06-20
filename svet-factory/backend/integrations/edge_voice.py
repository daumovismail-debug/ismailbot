"""edge-tts — БЕСПЛАТНЫЙ казахский (и любой) синтез речи нейроголосами Microsoft Edge.

Без ключей и регистрации. Казахские голоса: kk-KZ-AigulNeural (жен.),
kk-KZ-DauletNeural (муж.). Возвращает (mp3_bytes, word_timings), где word_timings —
тайминги слов [(start_sec, end_sec), ...] для ТОЧНОГО karaoke-синхрона субтитров.
"""
import asyncio

from .. import config

try:
    import edge_tts
    _IMPORTED = True
except Exception:  # noqa: BLE001
    _IMPORTED = False


def _log(msg: str) -> None:
    print(f"[edge-tts] {msg}", flush=True)


def available() -> bool:
    return config.USE_EDGE_TTS and _IMPORTED


async def _synth(text: str, voice: str):
    audio = bytearray()
    words: list[tuple[float, float]] = []
    comm = edge_tts.Communicate(text, voice)
    async for ch in comm.stream():
        t = ch.get("type")
        if t == "audio":
            audio.extend(ch["data"])
        elif t == "WordBoundary":
            start = ch["offset"] / 1e7                 # 100ns -> сек
            end = (ch["offset"] + ch["duration"]) / 1e7
            words.append((round(start, 3), round(end, 3)))
    return bytes(audio), words


def tts(text: str, voice: str | None = None):
    """Текст -> (mp3 bytes, word_timings) или (None, None) при ошибке/выкл."""
    if not available() or not (text or "").strip():
        return None, None
    try:
        audio, words = asyncio.run(_synth(text, voice or config.KZ_VOICE))
        return (audio or None), (words or None)
    except Exception as e:  # noqa: BLE001
        _log(f"ошибка синтеза: {e}")
        return None, None
