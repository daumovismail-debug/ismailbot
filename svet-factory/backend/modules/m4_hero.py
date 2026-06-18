"""МОДУЛЬ 4 — ГЕРОЙ. Эталонный кадр героини (для консистентности в кадрах)."""
from pathlib import Path

from .. import ffmpeg_tool, idea_bank
from ..integrations import gemini


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    hero_path = workdir / "hero.png"

    img = gemini.generate_image(idea_bank.HERO_PASSPORT)
    if img:
        hero_path.write_bytes(img)
        ctx["hero_image"] = img
        ctx["hero_path"] = str(hero_path)
        return "Эталон героини сгенерирован (Nano Banana Pro)"

    # демо-режим
    ffmpeg_tool.make_placeholder_image(hero_path, "ГЕРОИНЯ\n(демо-эталон)")
    ctx["hero_image"] = None
    ctx["hero_path"] = str(hero_path)
    return "Эталон героини: демо-плейсхолдер (нет ключа Gemini)"
