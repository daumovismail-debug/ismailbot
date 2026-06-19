"""МОДУЛЬ — АНАЛИТИК (прогноз, по analyst.md).

Оценивает серию ДО публикации: сила хука, риск слива, советы. Через LLM (по
рецепту) с веб-разведкой когда доступна; иначе — базовая эвристика по чек-листу.
"""
from .. import agent_runner


def _heuristic(scenes: list) -> dict:
    n = len(scenes)
    hook = scenes[0]["voice"] if scenes else ""
    score = 70
    if hook and len(hook.split()) <= 14:
        score += 10
    if any(s.get("role") == "КЛИФФХЭНГЕР" for s in scenes):
        score += 8
    if 10 <= n <= 14:
        score += 5
    score = min(score, 92)
    risks = [] if n >= 10 else [{"shot": n, "why": "мало кадров — история неясна"}]
    return {
        "mode": "predict", "hook_score": score,
        "predicted_intro_retention": "≈65-70%",
        "drop_risks": risks,
        "verdict": "потенциал хороший" if score >= 80 else "средне — усилить хук/середину",
        "fixes": ["держать твист в середине", "субтитры крупно для немого просмотра"],
    }


def run(job, ctx: dict) -> str:
    scenes = ctx.get("scenes", [])
    idea = ctx.get("idea", {})
    task = (
        f"Спрогнозируй виральность серии на тему «{idea.get('theme','')}». "
        f"Хук: «{scenes[0]['voice'] if scenes else ''}». Кадров: {len(scenes)}. "
        "Сделай веб-разведку трендов ниши, если можешь. Верни JSON (mode=predict, "
        "hook_score, predicted_intro_retention, drop_risks, verdict, fixes)."
    )
    data = agent_runner.run_json("analyst", task, session_key=f"svet-{job.id}")
    fc = data if isinstance(data, dict) and data.get("hook_score") is not None else _heuristic(scenes)
    src = "Аналитик (LLM+веб)" if (isinstance(data, dict) and data.get("hook_score") is not None) else "эвристика"
    ctx["forecast"] = fc
    return f"Прогноз ({src}): хук {fc.get('hook_score')}/100 — {fc.get('verdict','')}"
