"""МОДУЛЬ 3 — РАСКАДРОВКА (Художник + Аниматор-промпты).

Подключён к рецепту agents/artist.md через agent_runner (Этап B).
На каждый кадр: image_prompt (Style Bible + действие + свет-enum) и motion_prompt.
Без LLM — надёжный шаблон на основе Style Bible и канонной карты света.
"""
from .. import agent_runner, cast_library

# Style Bible (канон из project-bible.md / artist.md) — в каждый промпт без изменений.
STYLE_BASE = (
    "Pixar/Disney 3D animated film still, Unreal Engine 5 render, soft rounded "
    "shapes, smooth subsurface skin shading, warm cinematic lighting, vertical "
    "9:16, clean lower third for subtitles, no text in image."
)
DEFAULT_CHAR = (
    " CHARACTER (keep identical every shot): warm woman in her early 30s, soft "
    "heart-shaped face, large hazel eyes, natural dark hair, light-tan skin, "
    "modern everyday clothing; emotions read clearly on her face."
)
STYLE_BIBLE = STYLE_BASE + DEFAULT_CHAR


def _style_bible(brief: dict) -> str:
    """Style Bible с обликом героя из интервью (если задан) — чтобы во всех кадрах
    был ТОТ ЖЕ персонаж, которого описал Режиссёр."""
    look = (brief or {}).get("hero_look", "").strip()
    if not look:
        return STYLE_BIBLE
    return (STYLE_BASE + f" CHARACTER (keep identical every shot): {look}; "
            "emotions read clearly on the face.")

# Канонная карта «свет = эмоция» (enum -> визуал) — синхронно с project-bible.md.
LIGHT_MAP = {
    "happy": "bright warm light, eyes crinkled in a genuine smile, relaxed shoulders",
    "sad": "cool muted light, eyes welling, lip trembling, head lowered",
    "anger": "harsh red-tinted contrast light, brows furrowed, jaw clenched",
    "shock": "sudden hard light, deep shadows, eyes wide, frozen stare",
    "fear": "unstable dim light, dramatic shadows, wide darting eyes",
    "hope": "soft warm light growing golden, gentle hopeful smile, chin lifting",
    "despair": "cold dark low light, half-closed dull eyes, slumped posture",
    "resolve": "steady warm light, focused steady eyes, firm closed lips",
    "contempt": "cold side light, one-sided smirk, side glance",
}

_MOTION = {
    "COLD OPEN": "slow cinematic push-in on her face, slight handheld shake",
    "ЗАВЯЗКА": "gentle slow dolly across the warm room",
    "ПОВОРОТ": "snap zoom onto the key detail then her reaction, freeze",
    "ЭСКАЛАЦИЯ": "unstable handheld, tension rising",
    "КЛИФФХЭНГЕР": "slow push-in on her face, then cut to black",
}


def _template(scene: dict, extra_chars: list[dict], style_bible: str) -> dict:
    light = LIGHT_MAP.get(scene.get("light", ""), "warm cinematic light")
    beat = scene.get("beat", "")
    # лок второстепенных: подмешиваем их облик в промпт (чтобы были одинаковыми)
    extra = ""
    if extra_chars:
        extra = " Also in frame (keep identical): " + \
                "; ".join(cast_library.short_desc(c) for c in extra_chars) + "."
    return {
        "image_prompt": f"{style_bible} {light}. Scene: {beat}.{extra} vertical 9:16.",
        "motion_prompt": _MOTION.get(scene.get("role", ""), "smooth cinematic camera motion"),
    }


def run(job, ctx: dict) -> str:
    scenes = ctx["scenes"]
    cast = ctx.get("cast", [])
    by_cid = {c.get("id"): c for c in cast}
    style_bible = _style_bible(ctx.get("brief") or {})   # облик героя из интервью

    # 1) Пытаемся через Художника (LLM по рецепту artist.md)
    shots_brief = "\n".join(
        f'{s["id"]}. act={s.get("role")} light={s.get("light","")} action={s.get("beat","")}'
        for s in scenes
    )
    task = (
        "Для КАЖДОГО кадра ниже напиши image_prompt (англ., со Style Bible) и "
        "motion_prompt. Верни JSON-массив объектов "
        '[{"id":1,"image_prompt":"...","motion_prompt":"..."}].\n\nКадры:\n' + shots_brief
    )
    data = agent_runner.run_json("artist", task, session_key=f"svet-{job.id}")
    by_id = {}
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("id") is not None:
                by_id[item["id"]] = item

    storyboard = []
    used_llm = bool(by_id)
    for s in scenes:
        # кто в кадре: героиня (бренд-лид) + найденные второстепенные
        text = f'{s.get("voice","")} {s.get("voice_ru","")} {s.get("beat","")}'
        present = cast_library.present_ids(text, cast)
        refs = ["heroine"] + present
        extra_chars = [by_cid[i] for i in present if i in by_cid]

        item = by_id.get(s["id"])
        t = _template(s, extra_chars, style_bible)
        if item and item.get("image_prompt"):
            img_p = item["image_prompt"]
            # подмешиваем лок второстепенных и к промпту от LLM
            if extra_chars:
                img_p += " In frame (keep identical): " + \
                         "; ".join(cast_library.short_desc(by_cid[i]) for i in present) + "."
            mot_p = item.get("motion_prompt") or t["motion_prompt"]
        else:
            img_p, mot_p = t["image_prompt"], t["motion_prompt"]
        # КЛЮЧЕВОЕ: действие героя (что он ДЕЛАЕТ) обязано попасть в анимацию,
        # иначе клип = просто зум по статичной картинке («слайд-шоу»). Камера —
        # это t["motion_prompt"], а само действие живёт в beat (on_screen).
        action = (s.get("beat") or "").strip()
        if action and action.lower() not in mot_p.lower():
            mot_p = f"{mot_p}. Character action (animate this): {action}"
        storyboard.append({
            "id": s["id"],
            "role": s.get("role"),
            "voice": s.get("voice", ""),       # станет субтитром
            "image_prompt": img_p,
            "motion_prompt": mot_p,
            "references": refs,                 # лок лиц (SCHEMA): кто в кадре
        })

    ctx["storyboard"] = storyboard
    mode = "Художник (LLM)" if used_llm else "Художник на Style-Bible шаблоне"
    return f"Раскадровка на {len(storyboard)} кадров готова ({mode})"
