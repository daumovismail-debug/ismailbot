"""МОДУЛЬ 1 — ИДЕЯ + РЕЖИССЁР (бриф).

Выбирает тему-драму и формирует бриф (по director.md): тон, герой, конфликт,
тип хука, целевая эмоция. Бриф — единая истина для всей команды.
"""
from .. import agent_runner, idea_bank


def _demo_brief(idea: dict) -> dict:
    return {
        "idea": idea["theme"],
        "tone": "высокая драма, тревога",
        "hero": "heroine",
        "core_conflict": idea.get("message", idea["theme"]),
        "hook_type": "ультиматум",
        "target_emotion": "сопереживание + жажда продолжения",
        "visual_mood": "тёплый дом vs холодный свет ссоры",
        "series_link": "сезон про брак, деньги и признание",
    }


def run(job, ctx: dict) -> str:
    idea = idea_bank.pick(job.theme)
    ctx["idea"] = idea

    task = (
        f"Сделай бриф для серии на тему «{idea['theme']}» (посыл: {idea.get('message','')}). "
        "Верни JSON по своему формату (idea, tone, hero, core_conflict, hook_type, "
        "target_emotion, visual_mood, series_link)."
    )
    data = agent_runner.run_json("director", task, session_key=f"svet-{job.id}")
    ok = isinstance(data, dict) and "tone" in data
    brief = data if ok else _demo_brief(idea)
    ctx["brief"] = brief
    src = "Режиссёр (LLM)" if ok else "демо-бриф"
    return f"Тема: «{idea['theme']}». Бриф готов ({src}): тон «{brief.get('tone','')}»."
