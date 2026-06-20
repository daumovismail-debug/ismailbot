"""МОДУЛЬ 1 — ИДЕЯ + РЕЖИССЁР (бриф).

Выбирает тему-драму и формирует бриф (по director.md): тон, герой, конфликт,
тип хука, целевая эмоция, визуал, связь с сезоном. Бриф — единая истина для всей
команды: его читает Сценарист (Модуль 2) и далее. Поэтому бриф обязан быть ПОЛНЫМ
(все поля присутствуют) — недостающее от LLM добираем демо-значениями.
"""
from .. import agent_runner, idea_bank

# поля брифа по director.md — все обязаны присутствовать в выходе модуля
BRIEF_KEYS = ("idea", "tone", "hero", "core_conflict", "hook_type",
              "target_emotion", "visual_mood", "series_link")


def _demo_brief(idea: dict) -> dict:
    return {
        "idea": idea.get("theme", ""),
        "tone": "высокая драма, тревога",
        "hero": "heroine",
        "core_conflict": idea.get("message", idea.get("theme", "")),
        "hook_type": "ультиматум",
        "target_emotion": "сопереживание + жажда продолжения",
        "visual_mood": "тёплый дом vs холодный свет ссоры",
        "series_link": "сезон про брак, деньги и признание",
    }


def _merge(data: dict, idea: dict) -> dict:
    """Полный бриф: поле от LLM, если это непустая строка, иначе демо-значение."""
    brief = _demo_brief(idea)
    if isinstance(data, dict):
        for k in BRIEF_KEYS:
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                brief[k] = v.strip()
    brief["idea"] = idea.get("theme", "")  # тему подменить не даём
    return brief


def run(job, ctx: dict) -> str:
    idea = idea_bank.pick(job.theme)
    ctx["idea"] = idea

    task = (
        f"Сделай бриф для серии на тему «{idea['theme']}» (посыл: {idea.get('message','')}). "
        "Верни JSON по своему формату (idea, tone, hero, core_conflict, hook_type, "
        "target_emotion, visual_mood, series_link)."
    )
    data = agent_runner.run_json("director", task, session_key=f"svet-{job.id}")
    ok = (isinstance(data, dict)
          and isinstance(data.get("tone"), str) and bool(data["tone"].strip()))
    brief = _merge(data if ok else {}, idea)
    ctx["brief"] = brief
    src = "Режиссёр (LLM)" if ok else "демо-бриф"
    return (f"Тема: «{idea['theme']}». Бриф готов ({src}): "
            f"тон «{brief['tone']}», хук «{brief['hook_type']}», "
            f"эмоция-цель «{brief['target_emotion']}».")
