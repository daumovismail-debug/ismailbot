"""МОДУЛЬ 5 — КАРТИНКИ. 5 кадров сцен.

Приоритет: OpenClaw (подписка ChatGPT) -> OpenAI API -> плейсхолдер на монтаже.
Все кадры в одной сессии OpenClaw => героиня остаётся похожей.
"""
from pathlib import Path

from ..integrations import openai_api, openclaw_cli


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    storyboard = ctx["storyboard"]
    session_key = f"svet-{job.id}"

    progress = ctx.get("_progress")
    image_paths: list[str | None] = []
    real = 0
    engine = "демо"
    for i, shot in enumerate(storyboard):
        # чекпоинт: если кадр уже сгенерирован (повтор/докрутка) — переиспользуем
        existing = workdir / f"scene_{i}.png"
        if existing.exists() and existing.stat().st_size > 0:
            image_paths.append(str(existing))
            real += 1
            engine = "чекпоинт"
            continue
        if progress:
            progress(f"рисую кадр {i + 1}/{len(storyboard)}… (~1.5 мин на кадр)")
        img = openclaw_cli.generate_image(shot["image_prompt"], session_key=session_key)
        if img:
            engine = "OpenClaw"
        else:
            img = openai_api.generate_image(shot["image_prompt"])
            if img:
                engine = "OpenAI"
        if img:
            p = workdir / f"scene_{i}.png"
            p.write_bytes(img)
            image_paths.append(str(p))
            real += 1
        else:
            image_paths.append(None)

    ctx["image_paths"] = image_paths
    if real:
        return f"Сгенерировано кадров: {real}/{len(storyboard)} ({engine})"
    return f"Кадры: демо-режим, все {len(storyboard)} сцен будут плейсхолдерами"
