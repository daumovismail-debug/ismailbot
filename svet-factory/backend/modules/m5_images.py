"""МОДУЛЬ 5 — КАРТИНКИ. 5 кадров сцен с одним и тем же героем."""
from pathlib import Path

from ..integrations import gemini


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    hero_ref = ctx.get("hero_image")  # эталон для консистентности
    storyboard = ctx["storyboard"]

    image_paths: list[str | None] = []
    real = 0
    for i, shot in enumerate(storyboard):
        img = gemini.generate_image(shot["image_prompt"], ref_image=hero_ref)
        if img:
            p = workdir / f"scene_{i}.png"
            p.write_bytes(img)
            image_paths.append(str(p))
            real += 1
        else:
            image_paths.append(None)  # сцена пойдёт плейсхолдером

    ctx["image_paths"] = image_paths
    if real:
        return f"Сгенерировано кадров: {real}/{len(storyboard)} (Nano Banana Pro)"
    return f"Кадры: демо-режим, все {len(storyboard)} сцен будут плейсхолдерами"
