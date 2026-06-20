"""МОДУЛЬ 12 — ПРИЁМКА (вайб-ревью Режиссёра, по director.md).

Финальный приём готовой серии «по вайбу» (НЕ техника — техника у Контролёра).
Судит по 5 вопросам Режиссёра: хук, сопереживание, единый тон, клиффхэнгер,
связность сериала. Возвращает вердикт + заметки на доработку (ctx["review"]).
"""
from .. import agent_runner

PASS = 70   # порог приёмки по вайб-баллу


def _heuristic(brief: dict, scenes: list, qc: dict, episode_secs: int) -> dict:
    notes, score = [], 0
    roles = [s.get("role", "") for s in scenes]
    first = (scenes[0].get("voice", "") if scenes else "")

    # 1) хук с первой секунды
    if "COLD OPEN" in roles[:2] and first.strip():
        score += 22
    else:
        notes.append("Хук слабый: начни с cold open — самой острой реплики.")
    # 2) сопереживание герою (есть эмоциональная реплика-ультиматум/драма)
    if any(s.get("light") in ("anger", "despair", "sad", "shock") for s in scenes):
        score += 18
    else:
        notes.append("Мало эмоции у героя — добавь уязвимости/драмы.")
    # 3) единый тон (бриф задаёт тон, в кадрах есть его эмоции)
    if str(brief.get("tone", "")).strip():
        score += 18
    else:
        notes.append("Тон не задан Режиссёром — серия может «скакать».")
    # 4) клиффхэнгер на нерве
    if "КЛИФФХЭНГЕР" in roles[-2:]:
        score += 22
    else:
        notes.append("Нет резкого клиффхэнгера в финале — зритель не ждёт 2 серию.")
    # 5) связность с сезоном
    if str(brief.get("series_link", "")).strip():
        score += 10
    else:
        notes.append("Нет связи с аркой сезона.")
    # длина в норме (45–60) — мягкий штраф
    if not (40 <= episode_secs <= 62):
        score -= 8
        notes.append(f"Длина {episode_secs}с вне 45–60 — подгони темп.")
    # технический брак от Контролёра роняет приёмку
    if qc and qc.get("issues"):
        score -= 10
        notes.append("Контролёр нашёл дефекты — устрани перед публикацией.")

    score = max(0, min(100, score))
    accepted = score >= PASS and "COLD OPEN" in roles[:2] and "КЛИФФХЭНГЕР" in roles[-2:]
    verdict = "принято" if accepted else "на доработку"
    return {"vibe_score": score, "accepted": accepted, "verdict": verdict,
            "notes": notes or ["Вайб держит: хук, эмоция и клиффхэнгер на месте."]}


def run(job, ctx: dict) -> str:
    brief = ctx.get("brief", {})
    scenes = ctx.get("scenes", [])
    qc = ctx.get("qc", {})
    episode_secs = int(ctx.get("_episode_secs", 0))

    # пробуем живого Режиссёра (LLM по director.md)
    lines = "\n".join(f'{s.get("role","")}: {s.get("voice","")}' for s in scenes)
    task = (
        "Прими готовую серию ПО ВАЙБУ (не техника). Оцени по 5 вопросам: хук, "
        "сопереживание, единый тон, клиффхэнгер, связность сериала. Верни JSON "
        '{"vibe_score":0-100,"accepted":true/false,"verdict":"...","notes":["..."]}.\n'
        f"Бриф: тон={brief.get('tone','')}, эмоция-цель={brief.get('target_emotion','')}, "
        f"сезон={brief.get('series_link','')}.\nКадры:\n{lines}"
    )
    data = agent_runner.run_json("director", task, session_key=f"svet-{job.id}")
    ok = (isinstance(data, dict) and "vibe_score" in data
          and isinstance(data.get("notes"), list))
    review = data if ok else _heuristic(brief, scenes, qc, episode_secs)
    # подстрахуем обязательные поля
    review.setdefault("accepted", review.get("vibe_score", 0) >= PASS)
    review.setdefault("verdict", "принято" if review["accepted"] else "на доработку")
    review.setdefault("notes", [])
    ctx["review"] = review

    src = "Режиссёр (LLM)" if ok else "вайб-эвристика"
    mark = "✅ принято" if review["accepted"] else "⚠️ на доработку"
    return (f"Приёмка Режиссёра ({src}): {mark}, вайб {review['vibe_score']}/100. "
            + ("Замечания: " + "; ".join(review["notes"][:3]) if review["notes"] else ""))
