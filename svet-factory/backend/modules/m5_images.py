"""МОДУЛЬ 5 — КАРТИНКИ.

Художник: Pollinations (бесплатно, надёжно) -> OpenAI API (если есть ключ).
ChatGPT через OpenClaw в headless-режиме картинки не рисует, поэтому не зовём.
Vision-сверка лица — опционально (USE_FACE_QC=1), по умолчанию выкл.
"""
import hashlib
import os
from pathlib import Path

from .. import config
from ..integrations import grok_browser, openai_api, openclaw_cli, pollinations

FACE_MIN = 0.60
MAX_TRIES = 3


def _gen(prompt: str, session_key: str, seed: int | None = None,
         ref_url: str | None = None, debug_dir: str | None = None):
    # Grok через подписку (если включено) — рисует кадр в Pixar-стиле
    if config.USE_GROK_IMAGES:
        img = grok_browser.generate_image(prompt, debug_dir=debug_dir)
        if img:
            return img, "Grok (подписка)"
    # Слой 2: если есть эталон героя (ref_url) — рисуем «по образцу» (img2img),
    # чтобы лицо НЕ менялось от кадра к кадру. Не вышло — обычный текст->картинка.
    if ref_url:
        img = pollinations.generate_image(
            "Keep the SAME character identity, face and outfit as the reference "
            "image. " + prompt,
            seed=seed, image_url=ref_url, model=config.POLLINATIONS_EDIT_MODEL)
        if img:
            return img, "Pollinations (по эталону)"
    # Pollinations — надёжный бесплатный «художник». ChatGPT через OpenClaw в
    # фоновом (headless) режиме картинки НЕ рисует (у агента только bash),
    # поэтому его не зовём — иначе каждый кадр зря ждёт неудачу.
    img = pollinations.generate_image(prompt, seed=seed)
    if img:
        return img, "Pollinations"
    img = openai_api.generate_image(prompt)   # если задан OPENAI_API_KEY (платно)
    if img:
        return img, "OpenAI"
    return None, "демо"


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    storyboard = ctx["storyboard"]
    session_key = f"svet-{job.id}"
    hero = ctx.get("hero_path")
    # Слой 2 (консистентность): публичный адрес эталона героини — его показываем
    # художнику на каждом кадре. Нужен публичный media_base (PUBLIC_BASE_URL).
    media_base = ctx.get("media_base")
    hero_ref_url = None
    if config.USE_REF_IMAGES and media_base and hero and Path(hero).exists():
        hero_ref_url = f"{media_base}/{Path(hero).name}"
    # Слой 3: один фиксированный seed на всю серию — лицо не «скачет» случайно.
    seed = int(hashlib.md5(job.id.encode()).hexdigest(), 16) % 1_000_000
    # vision-сверка лица отключена: в headless-режиме у openclaw-агента нет
    # «зрения» (только bash), сверка всё равно вернёт None и лишь тормозит.
    # Включить можно флагом USE_FACE_QC=1, если появится рабочее зрение.
    can_check = (os.getenv("USE_FACE_QC", "0") == "1"
                 and openclaw_cli.available() and hero and Path(hero).exists())

    progress = ctx.get("_progress")
    qclog = ctx.get("_qclog")
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

        # эталон применяем к кадрам, где есть героиня (бренд-лид)
        ref_url = hero_ref_url if "heroine" in shot.get("references", []) else None
        best = None
        best_score = -1.0
        for attempt in range(1, MAX_TRIES + 1):
            if progress:
                progress(f"рисую кадр {i + 1}/{len(storyboard)}"
                         + (f" (попытка {attempt})" if attempt > 1 else "…"))
            img, eng = _gen(shot["image_prompt"], session_key,
                            seed=seed + i, ref_url=ref_url, debug_dir=str(workdir))
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
                if qclog and fm is not None:
                    qclog("КАРТИНКИ", f"кадр {i + 1}: лицо OK ({fm:.2f}) — принят", "ok")
                break  # лицо ок (или сверка недоступна)
            retries_total += 1                 # лицо «уплыло» — пробуем ещё
            if qclog:
                more = " — перерисовываю" if attempt < MAX_TRIES else " — лимит попыток, беру лучший"
                qclog("КАРТИНКИ",
                      f"кадр {i + 1}: лицо «уплыло» ({fm:.2f} < {FACE_MIN}){more}",
                      "retry")

        image_paths.append(best)
        if best:
            real += 1

    ctx["image_paths"] = image_paths
    ctx["frames_retries"] = retries_total
    if real:
        extra = f", переделок по лицу: {retries_total}" if retries_total else ""
        return f"Сгенерировано кадров: {real}/{len(storyboard)} ({engine}){extra}"
    return f"Кадры: демо-режим, все {len(storyboard)} сцен будут плейсхолдерами"
