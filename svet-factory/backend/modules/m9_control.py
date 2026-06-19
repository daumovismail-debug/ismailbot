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

    # vision-сверка лица с эталоном (если есть OpenClaw + эталон + кадры)
    face_scores: list[float] = []
    hero = ctx.get("hero_path")
    if openclaw_cli.available() and hero and Path(hero).exists():
        real_frames = [p for p in image_paths if p and Path(p).exists()]
        for p in real_frames[:3]:                 # выборка до 3 кадров (экономим вызовы)
            fm = openclaw_cli.compare_faces(hero, p)
            if fm is not None:
                face_scores.append(fm)
        bad = [s for s in face_scores if s < 0.60]
        if bad:
            issues.append(f"лицо «уплыло» на {len(bad)} из {len(face_scores)} (face_match<0.60)")

    avg_fm = round(sum(face_scores) / len(face_scores), 2) if face_scores else None
    ctx["qc"] = {"frames_ok": have, "frames_total": total,
                 "demo": not expect_real, "face_match_avg": avg_fm, "issues": issues}

    vision = (f"vision: face_match avg {avg_fm}" if avg_fm is not None
              else ("vision готов (нет кадров для сверки)" if openclaw_cli.available()
                    else "vision выкл (демо)"))
    if issues:
        return f"Контроль: ⚠️ {', '.join(issues)}. {vision}"
    if not expect_real:
        return f"Контроль: ✅ демо (плейсхолдеры), видео собрано, длина в норме. {vision}"
    return f"Контроль: ✅ проверки пройдены ({have}/{total} кадров, видео есть). {vision}"
