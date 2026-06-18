"""МОДУЛЬ 3 — РАСКАДРОВКА. Два агента-профи пишут промпты на каждую сцену.

🎨 Агент-Художник  -> промпт картинки (для ChatGPT)
🎬 Агент-Аниматор -> промпт движения (для Grok Imagine)
"""
from .. import agents
from ..integrations import openai_api


def run(job, ctx: dict) -> str:
    storyboard = []
    for scene in ctx["scenes"]:
        storyboard.append({
            "role": scene["role"],
            "voice": scene["voice"],
            "image_prompt": agents.image_prompt(scene),
            "motion_prompt": agents.motion_prompt(scene),
        })
    ctx["storyboard"] = storyboard
    mode = "агенты на ChatGPT" if openai_api.HAS_LLM else "агенты на шаблонах"
    return f"Раскадровка на {len(storyboard)} сцен готова ({mode})"
