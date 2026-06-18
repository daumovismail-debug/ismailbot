"""МОДУЛЬ 4 — ГЕРОЙ. Эталонный кадр героини.

Приоритет: OpenClaw (подписка ChatGPT) -> OpenAI API -> демо-плейсхолдер.
"""
from pathlib import Path

from .. import ffmpeg_tool, idea_bank
from ..integrations import openai_api, openclaw_cli


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    hero_path = workdir / "hero.png"
    session_key = f"svet-{job.id}"  # общая сессия => консистентная героиня

    progress = ctx.get("_progress")
    if progress:
        progress("рисую эталон героини… (~1.5 мин)")
    img = openclaw_cli.generate_image(idea_bank.HERO_PASSPORT, session_key=session_key)
    if img:
        hero_path.write_bytes(img)
        ctx["hero_path"] = str(hero_path)
        return "Эталон героини сгенерирован (OpenClaw / подписка ChatGPT)"

    img = openai_api.generate_image(idea_bank.HERO_PASSPORT)
    if img:
        hero_path.write_bytes(img)
        ctx["hero_path"] = str(hero_path)
        return "Эталон героини сгенерирован (OpenAI API)"

    ffmpeg_tool.make_placeholder_image(hero_path, "ГЕРОИНЯ\n(демо-эталон)")
    ctx["hero_path"] = str(hero_path)
    return "Эталон героини: демо-плейсхолдер (нет ни OpenClaw, ни OpenAI)"
