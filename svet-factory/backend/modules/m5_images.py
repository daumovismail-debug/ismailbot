"""МОДУЛЬ 5 — КАРТИНКИ. 5 кадров сцен (ChatGPT / gpt-image-1)."""
from pathlib import Path

from ..integrations import openai_api


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    storyboard = ctx["storyboard"]

    image_paths: list[str | None] = []
    real = 0
    for i, shot in enumerate(storyboard):
        img = openai_api.generate_image(shot["image_prompt"])
        if img:
            p = workdir / f"scene_{i}.png"
            p.write_bytes(img)
            image_paths.append(str(p))
            real += 1
        else:
            image_paths.append(None)  # сцена пойдёт плейсхолдером

    ctx["image_paths"] = image_paths
    if real:
        return f"Сгенерировано кадров: {real}/{len(storyboard)} (ChatGPT)"
    return f"Кадры: демо-режим, все {len(storyboard)} сцен будут плейсхолдерами"
