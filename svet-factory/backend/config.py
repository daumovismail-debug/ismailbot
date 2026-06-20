"""Конфигурация сервиса: ключи, модели, пути."""
import os
import shutil
from pathlib import Path

import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# --- API ключи ---
# Картинки делает ChatGPT (OpenAI), анимацию — Grok (xAI), озвучку — ElevenLabs.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
XAI_API_KEY = os.getenv("XAI_API_KEY", "").strip()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
# Telegram-хранилище готовых роликов (бот + канал/чат)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# --- Модели ---
OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
XAI_VIDEO_MODEL = os.getenv("XAI_VIDEO_MODEL", "grok-imagine-video")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

# Публичный адрес сервиса — нужен, чтобы Grok мог скачать наши картинки по URL.
# Например: http://164.92.255.154:8000
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")

# --- Параметры ролика ---
def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


SCENE_SECONDS = _int_env("SCENE_SECONDS", 5)
VIDEO_WIDTH = _int_env("VIDEO_WIDTH", 1080)
VIDEO_HEIGHT = _int_env("VIDEO_HEIGHT", 1920)
# Общий бюджет времени на анимацию всей серии (сек). Защита от зависания
# видео-движка: превысили — остаток кадров уходит на Ken Burns. 8 мин по умолчанию.
ANIMATE_BUDGET_SEC = _int_env("ANIMATE_BUDGET_SEC", 480)

# --- OpenClaw (генерация под подпиской ChatGPT/Grok через локальный CLI) ---
# Если на сервере установлен openclaw — картинки/видео идут через него
# (твоя подписка), без платных API. Это приоритетный движок.
OPENCLAW_BIN = shutil.which("openclaw")
OPENCLAW_AGENT = os.getenv("OPENCLAW_AGENT", "main")
USE_OPENCLAW = os.getenv("USE_OPENCLAW", "1") != "0" and bool(OPENCLAW_BIN)
# Видео через OpenClaw по умолчанию ВЫКЛ: оно может долго висеть, если у
# подписки нет видео-движка. Пока включаем -> анимация = плавный зум (Ken Burns).
# Поставь USE_OPENCLAW_VIDEO=1, когда подключишь рабочий видео-провайдер (Grok).
USE_OPENCLAW_VIDEO = os.getenv("USE_OPENCLAW_VIDEO", "0") == "1"

# --- Pollinations.ai (бесплатный генератор картинок, без ключей) ---
# Основной «художник»: OpenClaw картинки не умеет (только текст), поэтому
# изображения берём здесь — бесплатно и без регистрации.
USE_POLLINATIONS = os.getenv("USE_POLLINATIONS", "1") != "0"
POLLINATIONS_MODEL = os.getenv("POLLINATIONS_MODEL", "flux")

# Путь к бандл-бинарю ffmpeg (системный не требуется)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# Флаги доступности реальных интеграций
HAS_OPENCLAW = USE_OPENCLAW
HAS_OPENAI = bool(OPENAI_API_KEY)
HAS_XAI = bool(XAI_API_KEY)
HAS_ELEVENLABS = bool(ELEVENLABS_API_KEY)
HAS_TELEGRAM = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
HAS_POLLINATIONS = USE_POLLINATIONS
