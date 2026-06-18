"""Конфигурация сервиса: ключи, модели, пути."""
import os
from pathlib import Path

import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# --- API ключи ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()

# --- Модели ---
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")
GEMINI_VIDEO_MODEL = os.getenv("GEMINI_VIDEO_MODEL", "veo-3.1-generate-preview")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

# --- Параметры ролика ---
SCENE_SECONDS = int(os.getenv("SCENE_SECONDS", "5"))
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1080"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1920"))

# Путь к бандл-бинарю ffmpeg (системный не требуется)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# Флаги доступности реальных интеграций
HAS_GEMINI = bool(GEMINI_API_KEY)
HAS_ELEVENLABS = bool(ELEVENLABS_API_KEY)
