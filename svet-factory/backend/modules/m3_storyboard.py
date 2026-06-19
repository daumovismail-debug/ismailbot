"""МОДУЛЬ 3 — РАСКАДРОВКА (Художник + Аниматор-промпты).

Подключён к рецепту agents/artist.md через agent_runner (Этап B).
На каждый кадр: image_prompt (Style Bible + действие + свет-enum) и motion_prompt.
Без LLM — надёжный шаблон на основе Style Bible и канонной карты света.
"""
from .. import agent_runner

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


def _template(scene: dict) -> dict:
    light = LIGHT_MAP.get(scene.get("light", ""), "warm cinematic light")
    beat = scene.get("beat", "")
    return {
        "image_prompt": f"{STYLE_BIBLE} {light}. Scene: {beat}. vertical 9:16.",
        "motion_prompt": _MOTION.get(scene.get("role", ""), "smooth cinematic camera motion"),
    }


def run(job, ctx: dict) -> str:
    scenes = ctx["scenes"]

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
        item = by_id.get(s["id"])
        if item and item.get("image_prompt"):
            img_p = item["image_prompt"]
            mot_p = item.get("motion_prompt") or _template(s)["motion_prompt"]
        else:
            t = _template(s)
            img_p, mot_p = t["image_prompt"], t["motion_prompt"]
        storyboard.append({
            "id": s["id"],
            "role": s.get("role"),
            "voice": s.get("voice", ""),       # станет субтитром
            "image_prompt": img_p,
            "motion_prompt": mot_p,
            "references": ["heroine"],          # лок лица (SCHEMA)
        })

    ctx["storyboard"] = storyboard
    mode = "Художник (LLM)" if used_llm else "Художник на Style-Bible шаблоне"
    return f"Раскадровка на {len(storyboard)} кадров готова ({mode})"
