"""МОДУЛЬ 1 — ИДЕЯ. Выбирает тему-драму из банка идей."""
from .. import idea_bank


def run(job, ctx: dict) -> str:
    idea = idea_bank.pick(job.theme)
    ctx["idea"] = idea
    return f"Тема: «{idea['theme']}» — {idea['message']}"
