"""МОДУЛЬ 3 — РАСКАДРОВКА (Художник + Аниматор-промпты).

Подключён к рецепту agents/artist.md через agent_runner (Этап B).
На каждый кадр: image_prompt (Style Bible + действие + свет-enum) и motion_prompt.
Без LLM — надёжный шаблон на основе Style Bible и канонной карты света.
"""
from .. import agent_runner, cast_library

# Style Bible (канон из project-bible.md / artist.md) — в каждый промпт без изменений.
STYLE_BIBLE = (
    "Pixar/Disney 3D animated film still, Unreal Engine 5 render, soft rounded "
    "shapes, smooth subsurface skin shading, warm cinematic lighting, vertical "
    "9:16, clean lower third for subtitles, no text in image. Palette: warm gold, "
    "cream-beige, deep burgundy accents, soft charcoal shadows. CHARACTER (keep "
    "identical every shot): warm elegant woman in her early 30s, soft heart-shaped "
    "face, large hazel eyes, light-tan skin; instead of hair an elegant glowing "
    "crystal chandelier crown; cream-and-gold dress."
)

# Канонная карта «свет = эмоция» (enum -> визуал) — синхронно с project-bible.md.
LIGHT_MAP = {
    "happy": "chandelier-crown glowing bright warm gold, eyes crinkled in a smile",
    "sad": "crown dim and faint, cool muted light, eyes welling, lip trembling",
    "anger": "crown flickering red, harsh contrast, brows furrowed, jaw clenched",
    "shock": "sudden light flicker, deep shadows, eyes wide, frozen stare",
    "fear": "unstable trembling light, dramatic shadows, wide darting eyes",
    "hope": "warm light slowly growing golden, soft hopeful smile, chin lifting",
    "despair": "crown almost out, cold darkness, half-closed dull eyes",
    "resolve": "steady warm glow, focused steady eyes, firm closed lips",
    "contempt": "cold side light, one-sided smirk, side glance",
}

_MOTION = {
    "COLD OPEN": "slow cinematic push-in on her face, slight handheld shake",
    "ЗАВЯЗКА": "gentle slow dolly across the warm room",
    "ПОВОРОТ": "snap zoom onto the key detail then her reaction, freeze",
    "ЭСКАЛАЦИЯ": "unstable handheld, tension rising",
    "КЛИФФХЭНГЕР": "slow push-in on her face, then cut to black",
}


def _template(scene: dict, extra_chars: list[dict]) -> dict:
    light = LIGHT_MAP.get(scene.get("light", ""), "warm cinematic light")
    beat = scene.get("beat", "")
    # лок второстепенных: подмешиваем их облик в промпт (чтобы были одинаковыми)
    extra = ""
    if extra_chars:
        extra = " Also in frame (keep identical): " + \
                "; ".join(cast_library.short_desc(c) for c in extra_chars) + "."
    return {
        "image_prompt": f"{STYLE_BIBLE} {light}. Scene: {beat}.{extra} vertical 9:16.",
        "motion_prompt": _MOTION.get(scene.get("role", ""), "smooth cinematic camera motion"),
    }


def run(job, ctx: dict) -> str:
    scenes = ctx["scenes"]
    cast = ctx.get("cast", [])
    by_cid = {c.get("id"): c for c in cast}

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
        t = _template(s, extra_chars)
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
