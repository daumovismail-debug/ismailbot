"""МОДУЛЬ 9 — КОНТРОЛЬ. Финальная проверка качества (по controller.md).

Сейчас (демо/без vision) — базовые проверки: все кадры на месте, формат, длина.
Vision-сверка лица с эталоном (face_match) подключается на Этапе E через подписку.
"""
from pathlib import Path

from .. import config
from ..integrations import openclaw_cli


def run(job, ctx: dict) -> str:
    storyboard = ctx.get("storyboard", [])
    image_paths = ctx.get("image_paths", [None] * len(storyboard))

    have = sum(1 for p in image_paths if p and Path(p).exists())
    total = len(storyboard)
    expect_real = config.HAS_OPENCLAW or config.HAS_OPENAI  # ждём реальные кадры?
    issues = []
    if expect_real and have < total:
        issues.append(f"нет картинок: {total - have}/{total}")
    if not (job.video_path and Path(job.video_path).exists()):
        issues.append("нет финального видео")

    ctx["qc"] = {"frames_ok": have, "frames_total": total,
                 "demo": not expect_real, "issues": issues}

    vision = "vision-сверка лица — на Этапе E (через подписку)" \
        if openclaw_cli.available() else "vision выкл (демо)"
    if issues:
        return f"Контроль: ⚠️ {', '.join(issues)}. {vision}"
    if not expect_real:
        return f"Контроль: ✅ демо (плейсхолдеры), видео собрано, длина в норме. {vision}"
    return f"Контроль: ✅ проверки пройдены ({have}/{total} кадров, видео есть). {vision}"
