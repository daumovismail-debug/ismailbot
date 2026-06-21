"""МОДУЛЬ 10 — ПУБЛИКАЦИЯ. Готовит «пакет публикации» (по publisher.md).

Сам НЕ постит (API соцсетей ограничены) — собирает подпись/хэштеги/обложку/время,
чтобы выложить нативным планировщиком или вручную. Пишется в ctx["publish"].
"""
from .. import agent_runner, cleanup, config
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
    ok = isinstance(data, dict) and bool(data.get("caption"))
    pkg = data if ok else _demo_package(idea, scenes)
    source = "Издатель (LLM)" if ok else "демо-шаблон"
    # доставка готового ролика ФАЙЛОМ в Telegram-канал (если настроен) — полное
    # качество, скачиваешь оригиналом
    tg = telegram.send_document(job.video_path, pkg.get("caption", "")) if job.video_path else None
    cleaned = False
    if tg:
        pkg["telegram_url"] = tg
        # ролик теперь надёжно лежит в твоём Telegram-канале → чистим копию на
        # сервере, чтобы диск не забивался (его всегда можно скачать из Telegram)
        if config.AUTO_CLEANUP_AFTER_DOWNLOAD:
            cleaned = cleanup.cleanup_job_media(job)

    ctx["publish"] = pkg
    if tg:
        tg_note = f" Отправлен файлом в Telegram: {tg}." + \
                  (" Копия на сервере удалена (есть в Telegram)." if cleaned else "")
    else:
        tg_note = ""
    return (f"Пакет публикации готов ({source}): подпись + хэштеги + обложка + время."
            f"{tg_note}")
