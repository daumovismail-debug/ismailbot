"""МОДУЛЬ 6 — АНИМАЦИЯ. Оживляет кадры в видеоклипы.

Приоритет: OpenClaw (подписка Grok/видео) -> Grok API (xAI) -> на монтаже Ken Burns.
OpenClaw на том же сервере, поэтому отдаём ему локальный путь к картинке.
"""
from pathlib import Path

from .. import config
from ..integrations import openclaw_cli, xai


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    storyboard = ctx["storyboard"]
    image_paths = ctx.get("image_paths") or []
    media_base = ctx.get("media_base")
    session_key = f"svet-{job.id}"

    progress = ctx.get("_progress")
    video_paths: list[str | None] = []
    real = 0
    engine = "демо"
    for i, shot in enumerate(storyboard):
        if progress:
            progress(f"оживляю кадр {i + 1}/{len(storyboard)}…")
        clip = None
        img_path = image_paths[i] if i < len(image_paths) else None

        # 1) OpenClaw — отдаём локальный путь к кадру (только если явно включено,
        #    иначе пропускаем: видео может надолго зависать)
        if img_path and config.USE_OPENCLAW_VIDEO:
            clip = openclaw_cli.generate_video(
                shot["motion_prompt"], image_path=img_path, session_key=session_key
            )
            if clip:
                engine = "OpenClaw"

        # 2) запасной путь — Grok API по публичному URL кадра
        if not clip and img_path and media_base:
            url = f"{media_base}/{Path(img_path).name}"
            clip = xai.generate_video(shot["motion_prompt"], image_url=url)
            if clip:
                engine = "Grok API"

        if clip:
            p = workdir / f"clip_{i}.mp4"
            p.write_bytes(clip)
            video_paths.append(str(p))
            real += 1
        else:
            video_paths.append(None)  # на монтаже — Ken Burns по кадру

    ctx["video_paths"] = video_paths
    if real:
        return f"Оживлено клипов: {real}/{len(storyboard)} ({engine})"
    return "Анимация: плавный зум (Ken Burns) по кадрам — видео-движок отключён"
