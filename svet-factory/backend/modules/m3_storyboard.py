"""МОДУЛЬ 3 — РАСКАДРОВКА. На каждую сцену — промпт картинки и промпт движения."""
from .. import idea_bank

IMG_TPL = (
    "{hero} Scene: {beat}. Cinematic Pixar lighting, warm cozy interior, "
    "highly detailed, vertical 9:16."
)

MOTION_BY_ROLE = {
    "ХУК": "slow cinematic push-in on her face, chandelier-crown flickering softly",
    "ПРОБЛЕМА": "gentle camera pan across the warm room, light shining on others",
    "ДНО": "slow zoom out in a dim room, crystals dimming to near darkness",
    "ПЕРЕЛОМ": "warm golden light slowly growing brighter, she lifts her chin",
    "ФИНАЛ+CTA": "triumphant warm light fills the whole room, she smiles at camera",
}


def run(job, ctx: dict) -> str:
    hero = idea_bank.HERO_PASSPORT
    storyboard = []
    for scene in ctx["scenes"]:
        storyboard.append({
            "role": scene["role"],
            "voice": scene["voice"],
            "image_prompt": IMG_TPL.format(hero=hero, beat=scene.get("beat", "")),
            "motion_prompt": MOTION_BY_ROLE.get(
                scene["role"], "smooth cinematic camera motion"
            ),
        })
    ctx["storyboard"] = storyboard
    return f"Раскадровка на {len(storyboard)} сцен: промпты картинка+движение готовы"
