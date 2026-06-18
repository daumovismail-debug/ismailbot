"""МОДУЛЬ 2 — СЦЕНАРИЙ. 5 сцен по формуле Хук→Проблема→Дно→Перелом→Финал."""
import json

from ..integrations import openai_api, openclaw_cli

SCENE_ROLES = ["ХУК", "ПРОБЛЕМА", "ДНО", "ПЕРЕЛОМ", "ФИНАЛ+CTA"]

SCRIPT_SYSTEM = ("Ты — сценарист коротких вертикальных видео для женщин 30+ в нише "
                 "освещения/люстр. Пиши живо, цепляюще, с драмой.")

PROMPT = """Герой — Pixar-девушка с хрустальной люстрой-короной, её свет
отражает её эмоции (грустит — тускнеет, счастлива — сияет).

Тема: «{theme}»
Посыл: {message}

Напиши сценарий ровно на 5 сцен по формуле: ХУК, ПРОБЛЕМА, ДНО, ПЕРЕЛОМ, ФИНАЛ+CTA.
Для каждой сцены дай короткую реплику закадрового голоса (1 фраза, живая, цепляющая).
Верни СТРОГО JSON-массив из 5 объектов вида:
[{{"role":"ХУК","voice":"текст реплики","beat":"что происходит в кадре"}}]
Только JSON, без пояснений."""


def _fallback(idea: dict) -> list[dict]:
    """Базовый сценарий, если нет Gemini-ключа (демо-режим)."""
    voices = [
        "Раньше она освещала весь дом…",
        "Светила мужу, детям, гостям. Всем — кроме себя.",
        "И однажды её свет почти погас. А никто не обернулся.",
        "Пока она не вспомнила: этот свет — её. И гореть он должен для неё.",
        "Когда женщина светится для себя — сияет весь её дом. А ты давно зажигала свой свет?",
    ]
    beats = [
        "героиня в тёплой гостиной, её люстра-корона тускло мерцает, грустные глаза",
        "героиня освещает комнату, полную семьи, все наслаждаются светом, но не смотрят на неё",
        "героиня одна в тёмной комнате, корона почти погасла",
        "героиня у зеркала касается короны, загорается золотая искра, решимость",
        "героиня сияет тёплым светом, вся роскошная комната светится, счастливая улыбка",
    ]
    return [
        {"role": SCENE_ROLES[i], "voice": voices[i], "beat": beats[i]}
        for i in range(5)
    ]


def _parse(text: str) -> list[dict] | None:
    try:
        start = text.index("[")
        end = text.rindex("]") + 1
        scenes = json.loads(text[start:end])
        if isinstance(scenes, list) and len(scenes) >= 5:
            return scenes[:5]
    except Exception:  # noqa: BLE001
        pass
    return None


def run(job, ctx: dict) -> str:
    idea = ctx["idea"]
    user = PROMPT.format(theme=idea["theme"], message=idea["message"])

    # 1) OpenClaw (подписка ChatGPT) -> 2) OpenAI API -> 3) демо-шаблон
    raw = openclaw_cli.chat(f"{SCRIPT_SYSTEM}\n\n{user}", session_key=f"svet-{job.id}")
    source = "OpenClaw"
    if not (raw and _parse(raw)):
        raw = openai_api.chat(SCRIPT_SYSTEM, user)
        source = "ChatGPT API"

    scenes = _parse(raw) if raw else None
    if not scenes:
        scenes = _fallback(idea)
        source = "демо-шаблон"
    ctx["scenes"] = scenes
    return f"5 сцен готовы ({source}): " + " / ".join(s["role"] for s in scenes)
