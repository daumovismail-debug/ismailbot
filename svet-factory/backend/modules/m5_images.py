"""МОДУЛЬ 5 — КАРТИНКИ (с гейтом качества по кадру).

Приоритет: OpenClaw (подписка ChatGPT) -> OpenAI API -> плейсхолдер на монтаже.
Один общий сеанс OpenClaw => героиня похожа. Если доступна vision-сверка —
кадр с «уплывшим» лицом (face_match<0.60) перерисовывается, до 3 попыток (по SCHEMA).
"""
from pathlib import Path

from ..integrations import openai_api, openclaw_cli

FACE_MIN = 0.60
MAX_TRIES = 3


def _gen(prompt: str, session_key: str):
    img = openclaw_cli.generate_image(prompt, session_key=session_key)
    if img:
        return img, "OpenClaw"
    img = openai_api.generate_image(prompt)
    if img:
        return img, "OpenAI"
    return None, "демо"


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    storyboard = ctx["storyboard"]
    session_key = f"svet-{job.id}"
    hero = ctx.get("hero_path")
    can_check = openclaw_cli.available() and hero and Path(hero).exists()

    progress = ctx.get("_progress")
    image_paths: list[str | None] = []
    real = 0
    retries_total = 0
    engine = "демо"

    for i, shot in enumerate(storyboard):
        p = workdir / f"scene_{i}.png"
        # чекпоинт: уже есть — переиспользуем
        if p.exists() and p.stat().st_size > 0:
            image_paths.append(str(p))
            real += 1
            engine = "чекпоинт"
            continue

        best = None
        for attempt in range(1, MAX_TRIES + 1):
            if progress:
                progress(f"рисую кадр {i + 1}/{len(storyboard)}"
                         + (f" (попытка {attempt})" if attempt > 1 else "…"))
            img, eng = _gen(shot["image_prompt"], session_key)
            if not img:
                break
            engine = eng
            p.write_bytes(img)
            best = str(p)
            if not can_check:
                break  # нет vision — принимаем первый удачный
            fm = openclaw_cli.compare_faces(hero, str(p))
            if fm is None or fm >= FACE_MIN:
                break  # лицо ок (или сверка не сработала)
            retries_total += 1  # лицо «уплыло» — пробуем ещё

        image_paths.append(best)
        if best:
            real += 1

    ctx["image_paths"] = image_paths
    ctx["frames_retries"] = retries_total
    if real:
        extra = f", переделок по лицу: {retries_total}" if retries_total else ""
        return f"Сгенерировано кадров: {real}/{len(storyboard)} ({engine}){extra}"
    return f"Кадры: демо-режим, все {len(storyboard)} сцен будут плейсхолдерами"
