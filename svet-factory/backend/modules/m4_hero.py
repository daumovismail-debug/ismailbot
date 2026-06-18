"""МОДУЛЬ 4 — ГЕРОЙ. Эталонный кадр героини (ChatGPT / gpt-image-1)."""
from pathlib import Path

from .. import ffmpeg_tool, idea_bank
from ..integrations import openai_api


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    hero_path = workdir / "hero.png"

    img = openai_api.generate_image(idea_bank.HERO_PASSPORT)
    if img:
        hero_path.write_bytes(img)
        ctx["hero_path"] = str(hero_path)
        return "Эталон героини сгенерирован (ChatGPT)"

    # демо-режим
    ffmpeg_tool.make_placeholder_image(hero_path, "ГЕРОИНЯ\n(демо-эталон)")
    ctx["hero_path"] = str(hero_path)
    return "Эталон героини: демо-плейсхолдер (нет ключа OpenAI)"
