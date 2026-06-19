"""МОДУЛЬ 2 — СЦЕНАРИЙ (микро-драма, 10–14 кадров).

Подключён к рецепту agents/scenarist.md через agent_runner (Этап B).
Формат кадра ~ SCHEMA.md: {id, act, voice, beat, light}.
Без LLM — берём встроенный демо-сериал «Люстра или развод» (cold open + клиффхэнгер).
"""
from .. import agent_runner

TASK_TPL = (
    "Напиши Серию 1 микро-драмы на тему «{theme}». 10–14 кадров, формат строго по "
    "твоей инструкции (cold open → перемотка → повороты → клиффхэнгер). "
    "Верни JSON-объект с полем shots[] (id, act, voice_kz, voice_ru, on_screen, light)."
)

# Встроенный эталон на случай отсутствия LLM (демо-режим) — «Люстра или развод».
_DEMO = [
    ("COLD OPEN", "Купи мне эту люстру — или я ухожу!!", "героиня в слезах, чемодан у двери", "anger"),
    ("COLD OPEN", "Как мы до этого дошли? 3 дня назад…", "титр на чёрном", "sad"),
    ("ЗАВЯЗКА", "Эта люстра — мечта всей жизни.", "счастливая листает каталог", "happy"),
    ("ЗАВЯЗКА", "Смотри, какая красота!", "показывает мужу телефон", "happy"),
    ("ЗАВЯЗКА", "Ага, потом…", "муж отмахнулся, не глядя", "sad"),
    ("ПОВОРОТ", "Я всё-таки её заказала.", "колеблется у ценника, заказывает", "hope"),
    ("ПОВОРОТ", "Ты с ума сошла?! Это зарплата за месяц!", "муж увидел списание", "anger"),
    ("ПОВОРОТ", "А это что?! Часы втрое дороже!", "находит его чек — шок", "shock"),
    ("ЭСКАЛАЦИЯ", "Тебе можно, а мне нельзя?!", "ссора, крик", "anger"),
    ("ЭСКАЛАЦИЯ", "Гони эту транжиру! — голос свекрови.", "звонок свекрови, масла в огонь", "anger"),
    ("ЭСКАЛАЦИЯ", "Выбирай: люстра или развод.", "ставит чемодан, свет почти погас", "despair"),
    ("КЛИФФХЭНГЕР", "Алло… это насчёт развода?", "муж молча набирает телефон", "shock"),
    ("КЛИФФХЭНГЕР", "2 серия завтра 🔔 Кому он звонит?", "экран гаснет на её лице", "sad"),
]


def _from_llm(data) -> list[dict] | None:
    """Достаём кадры из ответа Сценариста (формат может слегка варьироваться)."""
    if isinstance(data, dict):
        shots = data.get("shots") or data.get("кадры")
    elif isinstance(data, list):
        shots = data
    else:
        shots = None
    if not shots or len(shots) < 8:
        return None
    scenes = []
    for i, s in enumerate(shots[:14], 1):
        voice = s.get("voice_ru") or s.get("voice_kz") or s.get("title") or ""
        scenes.append({
            "id": i,
            "role": s.get("act") or s.get("role") or "СЦЕНА",
            "voice": voice,
            "voice_kz": s.get("voice_kz", ""),
            "beat": s.get("on_screen") or s.get("action") or s.get("beat") or "",
            "light": s.get("light", ""),
        })
    return scenes


def run(job, ctx: dict) -> str:
    idea = ctx["idea"]
    data = agent_runner.run_json(
        "scenarist", TASK_TPL.format(theme=idea["theme"]), session_key=f"svet-{job.id}"
    )
    scenes = _from_llm(data)
    if scenes:
        source = "Сценарист (LLM)"
    else:
        scenes = [
            {"id": i + 1, "role": r, "voice": v, "voice_kz": "", "beat": b, "light": lt}
            for i, (r, v, b, lt) in enumerate(_DEMO)
        ]
        source = "демо-сериал"

    ctx["scenes"] = scenes
    return f"Сценарий готов ({source}): {len(scenes)} кадров, cold open → клиффхэнгер"
