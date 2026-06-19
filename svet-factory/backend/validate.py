"""Валидация контракта между этапами (по SCHEMA.md) — гейты надёжности.

Возвращает список предупреждений (строк). Пусто = всё чисто.
Цель: ловить «разъехавшиеся» данные ДО передачи дальше (риски 1–4 из orchestration).
"""
from pathlib import Path

from . import config


def validate(stage: str, ctx: dict) -> list[str]:
    w: list[str] = []
    scenes = ctx.get("scenes") or []
    sb = ctx.get("storyboard") or []

    if stage == "СЦЕНАРИЙ":
        if not (8 <= len(scenes) <= 14):
            w.append(f"кадров {len(scenes)} (ждём 10–14)")
        ids = [s.get("id") for s in scenes]
        if len(set(ids)) != len(ids) or any(i is None for i in ids):
            w.append("id кадров не уникальны/пусты")
        if any(not s.get("voice") for s in scenes):
            w.append("есть кадры без реплики")

    elif stage == "РАСКАДРОВКА":
        if len(sb) != len(scenes):
            w.append(f"кадров в раскадровке {len(sb)} ≠ сценарий {len(scenes)}")
        if any(not s.get("image_prompt") for s in sb):
            w.append("есть кадры без image_prompt")
        if any(not s.get("references") for s in sb):
            w.append("есть кадры без references (лок лица)")

    elif stage == "КАРТИНКИ":
        if config.HAS_OPENCLAW or config.HAS_OPENAI:
            paths = ctx.get("image_paths") or []
            have = sum(1 for p in paths if p and Path(p).exists())
            if have < len(sb):
                w.append(f"нарисовано {have}/{len(sb)} кадров")

    elif stage == "МОНТАЖ":
        vp = ctx.get("_video_path_check")
        # видео проверяет КОНТРОЛЬ; здесь — длина по числу кадров
        if len(sb) and ctx.get("_episode_secs", 0) > 60:
            w.append("длина >60 сек")

    return w
