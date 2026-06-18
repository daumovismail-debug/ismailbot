"""МОДУЛЬ 6 — АНИМАЦИЯ. Оживляет кадры в видеоклипы (Grok Imagine, image-to-video).

Grok забирает картинку по публичному URL, поэтому нужен config.PUBLIC_BASE_URL.
"""
from pathlib import Path

from .. import config
from ..integrations import xai


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    storyboard = ctx["storyboard"]
    image_paths = ctx["image_paths"]
    media_base = ctx.get("media_base")

    video_paths: list[str | None] = []
    real = 0
    skipped_no_url = False
    for i, shot in enumerate(storyboard):
        image_url = None
        if image_paths[i] and media_base:
            image_url = f"{media_base}/{Path(image_paths[i]).name}"
        elif image_paths[i] and not media_base:
            skipped_no_url = True

        clip = xai.generate_video(shot["motion_prompt"], image_url=image_url)
        if clip:
            p = workdir / f"clip_{i}.mp4"
            p.write_bytes(clip)
            video_paths.append(str(p))
            real += 1
        else:
            video_paths.append(None)  # на монтаже — Ken Burns / плейсхолдер

    ctx["video_paths"] = video_paths
    if real:
        return f"Оживлено клипов: {real}/{len(storyboard)} (Grok Imagine)"
    if skipped_no_url:
        return ("Анимация пропущена: не задан PUBLIC_BASE_URL — Grok не может "
                "скачать картинки. На монтаже применим Ken Burns по кадрам.")
    return "Анимация: демо-режим — на монтаже применим Ken Burns / плейсхолдеры"
