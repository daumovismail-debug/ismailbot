"""Автоуборка медиа серии с сервера, чтобы диск не забивался.

Удаляет и рабочую папку с кадрами (output/<job_id>/), и финальный ролик
(output/<job_id>.mp4). Используется и веб-скачиванием, и доставкой в Telegram.
"""
import shutil
from pathlib import Path

from . import config
from .jobs import store


def cleanup_job_media(job) -> bool:
    """Сносит кадры и финальный ролик серии. True — если что-то удалили."""
    out = config.OUTPUT_DIR.resolve()
    removed = False

    folder = (config.OUTPUT_DIR / job.id).resolve()
    if folder.is_dir() and folder.is_relative_to(out):
        shutil.rmtree(folder, ignore_errors=True)
        removed = True

    # финальный mp4 лежит РЯДОМ с папкой: output/<job_id>.mp4
    final = (config.OUTPUT_DIR / f"{job.id}.mp4").resolve()
    if final.is_file() and final.is_relative_to(out):
        final.unlink(missing_ok=True)
        removed = True

    job.video_path = None
    job.context.pop("workdir", None)
    store.save(job)
    if removed:
        print(f"[cleanup] медиа серии {job.id} удалены с сервера", flush=True)
    return removed
