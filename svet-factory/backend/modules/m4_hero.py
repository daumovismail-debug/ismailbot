"""МОДУЛЬ 4 — ГЕРОЙ / КАСТИНГ (по casting.md).

Собирает касту (паспорт героини), рисует ЭТАЛОН героини (face-lock) и МОДЕЛЬНЫЙ
ЛИСТ (turnaround + лист эмоций). Эталон и лист КЭШИРУЮТСЯ в cast/ и переиспользуются
между сериями — это консистентность №1 у Кастинга. Демо-плейсхолдеры НЕ кэшируются.

Приоритет генерации: OpenClaw (подписка ChatGPT) -> OpenAI API -> демо-плейсхолдер.
"""
from pathlib import Path
import shutil

from .. import config, ffmpeg_tool, idea_bank
from ..integrations import openai_api, openclaw_cli

# постоянный кэш ассетов касты (вне output/, не раздаётся через /media)
CAST_DIR = config.BASE_DIR / "cast"

# Паспорт бренд-героини (из casting.md) — каста сериала
HEROINE = {
    "id": "heroine", "name": "Героиня", "type": "human", "gender": "female", "age": 31,
    "face": "мягкое сердцевидное лицо, большие карие глаза, без волос — "
            "вместо них хрустальная люстра-корона (тёплое золото), светится по эмоции",
    "skin": "светло-смуглая", "outfit": "кремово-золотое платье",
    "signature": "корона-люстра, свет = эмоция", "character": "добрая, ранимая, сильная",
    "voice_hint": "тёплый искренний женский", "voice_id": "VOICE_HEROINE",
    "reference": "cast/heroine.png", "auto": False,
}

# Промпт модельного листа (из casting.md): turnaround + лист эмоций, делается 1 раз
MODEL_SHEET_PROMPT = (
    "character model sheet of the SAME character, multiple views in one image: "
    "front, 3/4, side, back, neutral A-pose, plus a row of facial expressions "
    "(happy, sad, angry, shock, hopeful). Consistent face and outfit across all "
    "views. Plain light-grey background, flat even lighting, vertical sheet layout. "
    + idea_bank.HERO_PASSPORT
)


def _gen(prompt: str, session_key: str) -> bytes | None:
    img = openclaw_cli.generate_image(prompt, session_key=session_key)
    if img:
        return img
    return openai_api.generate_image(prompt)


def _asset(cache: Path, dest: Path, prompt: str, session_key: str,
           placeholder_text: str, progress, progress_text: str) -> str:
    """Берём ассет из кэша, иначе генерим (и кэшируем реальный) либо плейсхолдер."""
    if cache.exists() and cache.stat().st_size > 0:
        shutil.copyfile(cache, dest)
        return "кэш касты"
    if progress:
        progress(progress_text)
    img = _gen(prompt, session_key)
    if img:
        dest.write_bytes(img)
        try:
            cache.write_bytes(img)   # кэшируем ТОЛЬКО реальный результат
        except Exception:  # noqa: BLE001
            pass
        return "OpenClaw/OpenAI"
    ffmpeg_tool.make_placeholder_image(dest, placeholder_text)
    return "демо-плейсхолдер"


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    session_key = f"svet-{job.id}"   # общая сессия => консистентная героиня
    CAST_DIR.mkdir(parents=True, exist_ok=True)
    ctx["cast"] = [HEROINE]
    progress = ctx.get("_progress")

    # 1) эталон героини — face-lock для Контролёра (кэш переиспользуем между сериями)
    hero_path = workdir / "hero.png"
    src = _asset(CAST_DIR / "heroine.png", hero_path, idea_bank.HERO_PASSPORT,
                 session_key, "ГЕРОИНЯ\n(демо-эталон)", progress,
                 "рисую эталон героини… (~1.5 мин)")
    ctx["hero_path"] = str(hero_path)

    # 2) модельный лист (turnaround + эмоции) — для Художника/Аниматора/Контролёра
    sheet_path = workdir / "model_sheet.png"
    sheet_src = _asset(CAST_DIR / "heroine_sheet.png", sheet_path, MODEL_SHEET_PROMPT,
                       session_key, "МОДЕЛЬНЫЙ ЛИСТ\nгероини (демо)", progress,
                       "рисую модельный лист героини…")
    ctx["model_sheet"] = str(sheet_path)

    return f"Каста: героиня (паспорт). Эталон — {src}; модельный лист — {sheet_src}."
