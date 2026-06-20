"""МОДУЛЬ 5 — КАРТИНКИ (с гейтом качества по кадру).

Приоритет: OpenClaw (подписка ChatGPT) -> OpenAI API -> плейсхолдер на монтаже.
Один общий сеанс OpenClaw => героиня похожа. Если доступна vision-сверка —
кадр с «уплывшим» лицом (face_match<0.60) перерисовывается, до 3 попыток (по SCHEMA).
"""
from pathlib import Path

from ..integrations import openai_api, openclaw_cli, pollinations

FACE_MIN = 0.60
MAX_TRIES = 3


def _gen(prompt: str, session_key: str):
    # Pollinations — основной «художник» (бесплатно, без ключей)
    img = pollinations.generate_image(prompt)
    if img:
        return img, "Pollinations"
    img = openai_api.generate_image(prompt)
    if img:
        return img, "OpenAI"
    img = openclaw_cli.generate_image(prompt, session_key=session_key)
    if img:
        return img, "OpenClaw"
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
        best_score = -1.0
        for attempt in range(1, MAX_TRIES + 1):
            if progress:
                progress(f"рисую кадр {i + 1}/{len(storyboard)}"
                         + (f" (попытка {attempt})" if attempt > 1 else "…"))
            img, eng = _gen(shot["image_prompt"], session_key)
            if not img:
                break
            engine = eng
            if not can_check:
                p.write_bytes(img)
                best = str(p)
                break  # нет vision — принимаем первый удачный
            # есть vision: сверяем во временный файл, оставляем кадр с ЛУЧШИМ лицом
            tmp = workdir / f"scene_{i}.try{attempt}.png"
            tmp.write_bytes(img)
            fm = openclaw_cli.compare_faces(hero, str(tmp))
            score = 1.0 if fm is None else fm   # сверка не сработала — не штрафуем
            if score > best_score:
                best_score = score
                tmp.replace(p)                 # лучший пока — в scene_{i}.png
                best = str(p)
            else:
                tmp.unlink(missing_ok=True)
            if fm is None or fm >= FACE_MIN:
                break  # лицо ок (или сверка недоступна)
            retries_total += 1                 # лицо «уплыло» — пробуем ещё

        image_paths.append(best)
        if best:
            real += 1

    ctx["image_paths"] = image_paths
    ctx["frames_retries"] = retries_total
    if real:
        extra = f", переделок по лицу: {retries_total}" if retries_total else ""
        return f"Сгенерировано кадров: {real}/{len(storyboard)} ({engine}){extra}"
    return f"Кадры: демо-режим, все {len(storyboard)} сцен будут плейсхолдерами"
