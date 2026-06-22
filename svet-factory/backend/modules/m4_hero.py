"""МОДУЛЬ 4 — ГЕРОЙ / ЭТАЛОНЫ КАСТЫ (по casting.md).

Рисует ЭТАЛОН каждого персонажа из подтверждённой касты (face-lock) + МОДЕЛЬНЫЙ
ЛИСТ героини (turnaround + эмоции). Эталоны КЭШИРУЮТСЯ в cast/ по id персонажа и
переиспользуются между сериями — это консистентность №1 у Кастинга. Демо-плейсхолдеры
НЕ кэшируются.

Приоритет генерации: OpenClaw (подписка ChatGPT) -> OpenAI API -> демо-плейсхолдер.
"""
from pathlib import Path

from .. import cast_library, config, ffmpeg_tool, idea_bank
from ..integrations import grok_browser, openai_api, openclaw_cli, pollinations

# постоянный кэш ассетов касты (вне output/, не раздаётся через /media)
CAST_DIR = config.BASE_DIR / "cast"

# Промпт модельного листа героини (из casting.md): turnaround + лист эмоций
MODEL_SHEET_PROMPT = (
    "character model sheet of the SAME character, multiple views in one image: "
    "front, 3/4, side, back, neutral A-pose, plus a row of facial expressions "
    "(happy, sad, angry, shock, hopeful). Consistent face and outfit across all "
    "views. Plain light-grey background, flat even lighting, vertical sheet layout. "
    + idea_bank.HERO_PASSPORT
)


def _gen(prompt: str, session_key: str, debug_dir: str | None = None) -> bytes | None:
    # Grok включён → рисует ТОЛЬКО Grok (без бесплатного запасного). Не вышло —
    # вернём None, дальше будет заглушка (видно, что Grok не сработал — починим).
    if config.USE_GROK_IMAGES:
        return grok_browser.generate_image(prompt, debug_dir=debug_dir)
    # Grok выключен → обычный «художник» (Pollinations и т.д.)
    img = pollinations.generate_image(prompt)
    if img:
        return img
    img = openai_api.generate_image(prompt)
    if img:
        return img
    return openclaw_cli.generate_image(prompt, session_key=session_key)


def _asset(cache: Path, dest: Path, prompt: str, session_key: str,
           placeholder_text: str, progress, progress_text: str) -> str:
    """Берём ассет из кэша, иначе генерим (и кэшируем реальный) либо плейсхолдер."""
    if cache.exists() and cache.stat().st_size > 0:
        dest.write_bytes(cache.read_bytes())
        return "кэш касты"
    if progress:
        progress(progress_text)
    img = _gen(prompt, session_key, debug_dir=str(dest.parent))
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
    session_key = f"svet-{job.id}"   # общая сессия => консистентные персонажи
    CAST_DIR.mkdir(parents=True, exist_ok=True)
    cast = ctx.get("cast") or [dict(cast_library.HEROINE)]
    progress = ctx.get("_progress")
    # облик главной героини — из брифа Режиссёра (внешность, что выяснили в интервью)
    brief = ctx.get("brief") or {}
    hero_pp = cast_library.hero_passport(brief.get("hero_look", ""),
                                         idea_bank.HERO_PASSPORT)

    srcs = []
    for c in cast:
        cid = c.get("id", "char")
        prompt = cast_library.passport_prompt(c, hero_pp)
        dest = workdir / ("hero.png" if cid == "heroine" else f"char_{cid}.png")
        src = _asset(CAST_DIR / f"{cid}.png", dest, prompt, session_key,
                     f"{c.get('name','')}\n(демо-эталон)", progress,
                     f"рисую эталон: {c.get('name','')}…")
        c["_ref"] = dest.name
        srcs.append(f"{c.get('name','')} — {src}")
        if cid == "heroine":
            ctx["hero_path"] = str(dest)   # face-lock героини для Контролёра
            sheet = workdir / "model_sheet.png"
            _asset(CAST_DIR / "heroine_sheet.png", sheet, MODEL_SHEET_PROMPT,
                   session_key, "МОДЕЛЬНЫЙ ЛИСТ\nгероини (демо)", progress,
                   "рисую модельный лист героини…")
            ctx["model_sheet"] = str(sheet)

    ctx["cast"] = cast
    return "Эталоны касты готовы: " + "; ".join(srcs)
