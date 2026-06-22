"""Конфигурация сервиса: ключи, модели, пути."""
import os
import shutil
from pathlib import Path

import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Удалять кадры/видео серии с сервера сразу после скачивания (экономит место на диске).
# Включено по умолчанию. Отключить: AUTO_CLEANUP_AFTER_DOWNLOAD=0
AUTO_CLEANUP_AFTER_DOWNLOAD = os.getenv("AUTO_CLEANUP_AFTER_DOWNLOAD", "1") == "1"

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
# Целевая длина всей серии (сек). Сериальная драма (ReelShort/DramaBox) — около
# 1 минуты на серию. Из неё считается длина кадра: EPISODE_TARGET_SEC / число_кадров.
EPISODE_TARGET_SEC = _int_env("EPISODE_TARGET_SEC", 65)
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

# --- Grok-видео через ПОДПИСКУ (автоматизация браузера grok.com, без API-ключа) ---
# ВЫКЛ по умолчанию: нужен сервер >=2 ГБ + сохранённая сессия grok.com. См. README.
USE_GROK_BROWSER = os.getenv("USE_GROK_BROWSER", "0") == "1"
# Рисовать КАРТИНКИ через Grok (а не только видео). Отдельный тумблер: включаем,
# когда сессия grok.com настроена и проверена. Иначе картинки — через Pollinations.
USE_GROK_IMAGES = os.getenv("USE_GROK_IMAGES", "0") == "1"
GROK_URL = os.getenv("GROK_URL", "https://grok.com/imagine")
GROK_STATE_FILE = os.getenv("GROK_STATE_FILE", str(BASE_DIR / ".state" / "grok_state.json"))
GROK_WAIT_MS = _int_env("GROK_WAIT_MS", 180_000)   # сколько ждём готовое видео
GROK_IMG_WAIT_MS = _int_env("GROK_IMG_WAIT_MS", 90_000)  # доза-ожидание чёткой картинки
# селекторы grok.com (могут поменяться — тогда правим тут через .env)
GROK_SEL_PROMPT = os.getenv("GROK_SEL_PROMPT", '[aria-label="Ask Grok anything"]')
GROK_SEL_SUBMIT = os.getenv("GROK_SEL_SUBMIT", "button[type=submit]")
GROK_SEL_RESULT_IMG = os.getenv("GROK_SEL_RESULT_IMG", "")  # пусто = авто-эвристика

# --- Pollinations.ai (бесплатный генератор картинок, без ключей) ---
# Основной «художник»: OpenClaw картинки не умеет (только текст), поэтому
# изображения берём здесь — бесплатно и без регистрации.
USE_POLLINATIONS = os.getenv("USE_POLLINATIONS", "1") != "0"
POLLINATIONS_MODEL = os.getenv("POLLINATIONS_MODEL", "flux")
# Модель для режима «по картинке-образцу» (image-to-image): сохраняет лицо героя
# из эталона в каждом кадре. kontext (Flux Kontext) умеет принимать образец.
POLLINATIONS_EDIT_MODEL = os.getenv("POLLINATIONS_EDIT_MODEL", "kontext")
# Рисовать кадры от эталона героя (консистентность лица). Можно выключить =0.
USE_REF_IMAGES = os.getenv("USE_REF_IMAGES", "1") != "0"

# --- Казахский голос: edge-tts (нейроголоса Microsoft Edge, БЕСПЛАТНО) ---
# Без ключей. Голоса: kk-KZ-AigulNeural (жен.), kk-KZ-DauletNeural (муж.).
USE_EDGE_TTS = os.getenv("USE_EDGE_TTS", "1") != "0"
KZ_VOICE = os.getenv("KZ_VOICE", "kk-KZ-AigulNeural")

# Путь к бандл-бинарю ffmpeg (системный не требуется)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# Флаги доступности реальных интеграций
HAS_OPENCLAW = USE_OPENCLAW
HAS_OPENAI = bool(OPENAI_API_KEY)
HAS_XAI = bool(XAI_API_KEY)
HAS_ELEVENLABS = bool(ELEVENLABS_API_KEY)
HAS_TELEGRAM = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
HAS_POLLINATIONS = USE_POLLINATIONS
HAS_VOICE = USE_EDGE_TTS or bool(ELEVENLABS_API_KEY)
