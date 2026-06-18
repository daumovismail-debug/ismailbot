"""Два агента-профи по промптам.

🎨 Агент-Художник  — пишет промпты для картинок (ChatGPT / gpt-image-1)
🎬 Агент-Аниматор — пишет промпты для оживления (Grok Imagine, image-to-video)

Если есть ключ OpenAI — агенты «думают» через LLM и пишут промпт под конкретную
сцену. Если ключа нет — работают на сильных профессиональных шаблонах
(демо-режим), чтобы сервис всегда выдавал результат.
"""
from . import idea_bank
from .integrations import openai_api

# --- Системные роли агентов (их «профессия») ---

IMAGE_AGENT_SYSTEM = """Ты — топовый промпт-инженер для генерации изображений в
ChatGPT (модель gpt-image-1). Твоя специализация — кадры в стиле Pixar/Disney 3D
для вертикальных коротких видео.

Правила хорошего промпта:
- описывай ОДНУ сцену: кто в кадре, эмоция, поза, действие, окружение, свет;
- всегда держи единый стиль: Pixar 3D render, soft cinematic lighting, warm tones;
- вертикальная композиция 9:16, место под субтитр снизу;
- НИКАКОГО текста на картинке;
- пиши промпт на английском, 2–4 плотных предложения, без воды и без пояснений.
Верни ТОЛЬКО сам промпт."""

ANIM_AGENT_SYSTEM = """Ты — топовый промпт-инженер для image-to-video в Grok Imagine.
Твоя задача — описать ДВИЖЕНИЕ для оживления уже готового кадра.

Правила:
- описывай только движение: ход камеры, динамику света, мелкие движения героя,
  атмосферу (частицы, блики), физику;
- НЕ переописывай содержимое кадра заново — он уже есть;
- движение плавное, кинематографичное, 5 секунд;
- пиши на английском, 1–2 предложения, без пояснений.
Верни ТОЛЬКО сам промпт движения."""


# --- Профессиональные шаблоны (демо-режим, без LLM) ---

_MOTION_BY_ROLE = {
    "ХУК": "slow cinematic push-in on her face, chandelier-crown flickering softly, "
           "faint dust particles drifting in warm light",
    "ПРОБЛЕМА": "gentle camera pan across the warm room, her light shining on others, "
                "subtle shifts of golden glow",
    "ДНО": "slow camera pull-back in a dim room, crystals dimming to near darkness, "
           "cold shadows creeping in",
    "ПЕРЕЛОМ": "warm golden light slowly growing brighter, she lifts her chin, "
               "glowing sparks rising around her crown",
    "ФИНАЛ+CTA": "triumphant warm light blooms and fills the whole room, "
                 "she smiles at camera, lens flares and soft bokeh",
}


def image_prompt(scene: dict) -> str:
    """🎨 Агент-Художник: промпт картинки под сцену."""
    hero = idea_bank.HERO_PASSPORT
    beat = scene.get("beat", "")
    if openai_api.HAS_LLM:
        user = (f"Персонаж (держи его одинаковым): {hero}\n"
                f"Роль сцены: {scene.get('role')}\n"
                f"Что происходит: {beat}\n"
                f"Напиши промпт для картинки этой сцены.")
        out = openai_api.chat(IMAGE_AGENT_SYSTEM, user)
        if out:
            return out.strip()
    # шаблон
    return (f"{hero} Scene: {beat}. Cinematic Pixar 3D render, soft warm lighting, "
            f"cozy interior, highly detailed, vertical 9:16 composition, "
            f"space at the bottom for subtitles, no text in image.")


def motion_prompt(scene: dict) -> str:
    """🎬 Агент-Аниматор: промпт движения под сцену."""
    if openai_api.HAS_LLM:
        user = (f"Роль сцены: {scene.get('role')}\n"
                f"Что в кадре: {scene.get('beat', '')}\n"
                f"Реплика: {scene.get('voice', '')}\n"
                f"Опиши движение для оживления этого кадра в Grok Imagine.")
        out = openai_api.chat(ANIM_AGENT_SYSTEM, user)
        if out:
            return out.strip()
    return _MOTION_BY_ROLE.get(scene.get("role"), "smooth cinematic camera motion")
