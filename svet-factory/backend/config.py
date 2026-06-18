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

# --- Модели ---
OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
XAI_VIDEO_MODEL = os.getenv("XAI_VIDEO_MODEL", "grok-imagine-video")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

# Публичный адрес сервиса — нужен, чтобы Grok мог скачать наши картинки по URL.
# Например: http://164.92.255.154:8000
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")

# --- Параметры ролика ---
SCENE_SECONDS = int(os.getenv("SCENE_SECONDS", "5"))
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1080"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1920"))

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

# Путь к бандл-бинарю ffmpeg (системный не требуется)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# Флаги доступности реальных интеграций
HAS_OPENCLAW = USE_OPENCLAW
HAS_OPENAI = bool(OPENAI_API_KEY)
HAS_XAI = bool(XAI_API_KEY)
HAS_ELEVENLABS = bool(ELEVENLABS_API_KEY)
