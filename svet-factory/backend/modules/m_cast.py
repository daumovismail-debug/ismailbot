"""МОДУЛЬ КАСТИНГ (по casting.md) — гибрид: находит персонажей и СПРАШИВАЕТ.

После сценария выписывает нужных персонажей (героиня + второстепенные из реплик),
кладёт их в ctx["cast"] как предложение и СТАВИТ ПАУЗУ: пользователь в интерфейсе
правит/добавляет или жмёт «пусть решит сам». Затем конвейер продолжается.

PAUSE_AFTER=True — сигнал оркестратору остановиться после этого модуля.
"""
from .. import cast_library

PAUSE_AFTER = True


def run(job, ctx: dict) -> str:
    scenes = ctx.get("scenes", [])
    # если каста уже подтверждена пользователем (резюме после паузы) — не трогаем
    if ctx.get("cast_confirmed"):
        cast = ctx.get("cast", [])
        names = ", ".join(c.get("name", "") for c in cast)
        return f"Каста подтверждена: {names}. Лица будут залочены по эталонам."

    cast = cast_library.detect(scenes)
    ctx["cast"] = cast
    names = ", ".join(c.get("name", "") for c in cast)
    extra = len(cast) - 1
    return (f"Найдены персонажи: {names}"
            + (f" (+{extra} второстеп.)" if extra else "")
            + ". Подтверди или поправь касту, затем продолжим.")
