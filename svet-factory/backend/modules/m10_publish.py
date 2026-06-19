"""МОДУЛЬ 10 — ПУБЛИКАЦИЯ. Готовит «пакет публикации» (по publisher.md).

Сам НЕ постит (API соцсетей ограничены) — собирает подпись/хэштеги/обложку/время,
чтобы выложить нативным планировщиком или вручную. Пишется в ctx["publish"].
"""
from .. import agent_runner
from ..integrations import telegram


def _demo_package(idea: dict, scenes: list) -> dict:
    hook = scenes[0]["voice"] if scenes else idea.get("theme", "")
    return {
        "platforms": ["tiktok", "reels", "shorts"],
        "caption": f"{hook} Угадаешь, что дальше? 👀 #люстра #семья",
        "hashtags": ["#люстра", "#интерьердома", "#женскиеистории", "#сериал"],
        "cover": {"text": idea.get("theme", ""), "frame": "cold open"},
        "first_comment": "2 серия завтра 🔔 Как думаешь, чем закончится?",
        "post_time": "Сб 09:00 / Вт 18:00 local",
        "cta": "подпишись, чтобы не пропустить 2 серию",
    }


def run(job, ctx: dict) -> str:
    idea = ctx.get("idea", {})
    scenes = ctx.get("scenes", [])
    task = (
        f"Собери «пакет публикации» для серии на тему «{idea.get('theme','')}». "
        f"Хук первой сцены: «{scenes[0]['voice'] if scenes else ''}». "
        "Верни JSON по своему формату (caption, hashtags, cover, first_comment, post_time, cta)."
    )
    data = agent_runner.run_json("publisher", task, session_key=f"svet-{job.id}")
    pkg = data if isinstance(data, dict) and data.get("caption") else _demo_package(idea, scenes)
    source = "Издатель (LLM)" if (isinstance(data, dict) and data.get("caption")) else "демо-шаблон"
    # выгрузка готового ролика в Telegram-архив (если настроен)
    tg = telegram.send_video(job.video_path, pkg.get("caption", "")) if job.video_path else None
    if tg:
        pkg["telegram_url"] = tg

    ctx["publish"] = pkg
    tg_note = f" Залит в Telegram: {tg}" if tg else ""
    return (f"Пакет публикации готов ({source}): подпись + хэштеги + обложка + время."
            f"{tg_note} Постинг — вручную/планировщиком.")
