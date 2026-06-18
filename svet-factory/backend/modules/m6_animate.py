"""МОДУЛЬ 6 — АНИМАЦИЯ. Оживляет кадры в видеоклипы (Veo 3.1)."""
from pathlib import Path

from ..integrations import gemini


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    storyboard = ctx["storyboard"]
    image_paths = ctx["image_paths"]

    video_paths: list[str | None] = []
    real = 0
    for i, shot in enumerate(storyboard):
        img_bytes = None
        if image_paths[i]:
            img_bytes = Path(image_paths[i]).read_bytes()
        clip = gemini.generate_video(shot["motion_prompt"], image=img_bytes)
        if clip:
            p = workdir / f"clip_{i}.mp4"
            p.write_bytes(clip)
            video_paths.append(str(p))
            real += 1
        else:
            video_paths.append(None)  # упадём на Ken Burns / плейсхолдер при монтаже

    ctx["video_paths"] = video_paths
    if real:
        return f"Оживлено клипов: {real}/{len(storyboard)} (Veo 3.1)"
    return "Анимация: демо-режим — на монтаже применим Ken Burns / плейсхолдеры"
