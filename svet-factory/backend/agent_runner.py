"""Движок агентов: читает рецепт agents/<name>.md и исполняет его через LLM.

Связывает «чертёж» (спеки агентов) с кодом (Этап B). Приоритет LLM:
OpenClaw (подписка ChatGPT) -> OpenAI API -> None (тогда модуль берёт демо-фоллбэк).
"""
import json
import re
from pathlib import Path

from . import config
from .integrations import openai_api, openclaw_cli

AGENTS_DIR = config.BASE_DIR / "agents"


def load_spec(name: str) -> str:
    p = AGENTS_DIR / f"{name}.md"
    try:
        return p.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return ""


def _parse_json(raw: str | None):
    """Достаём JSON-объект или массив из ответа LLM."""
    if not raw:
        return None
    for opener, closer in (("[", "]"), ("{", "}")):
        try:
            s = raw.index(opener)
            e = raw.rindex(closer) + 1
            return json.loads(raw[s:e])
        except (ValueError, json.JSONDecodeError):
            continue
    return None


def run_json(agent_name: str, task: str, session_key: str | None = None):
    """Запускает агента по его рецепту, возвращает распарсенный JSON или None."""
    spec = load_spec(agent_name)
    if not spec:
        return None
    prompt = (
        f"{spec}\n\n# ЗАДАЧА\n{task}\n\n"
        "Верни СТРОГО валидный JSON по формату из инструкции выше. "
        "Без markdown, без пояснений — только JSON."
    )
    raw = openclaw_cli.chat(prompt, session_key=session_key)
    if not raw:
        raw = openai_api.chat("Ты — агент продакшн-команды. Отвечай только JSON.", prompt)
    return _parse_json(raw)


def llm_available() -> bool:
    return openclaw_cli.available() or openai_api.HAS_LLM
