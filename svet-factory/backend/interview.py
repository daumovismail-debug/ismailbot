"""Интервью-продюсер: подробный диалог с автором ПЕРЕД запуском конвейера.

Продюсер по-человечески расспрашивает автора (герой, конфликт, сеттинг, тон,
аудитория, хук, концовка, визуал, язык реплик) и в конце выдаёт ПОЛНЫЙ бриф —
единую истину, которую дальше читают Режиссёр/Сценарист/Художник
(см. m1_idea.BRIEF_KEYS и m2_script — бриф уже передаётся в задачу агентам).

Состояние диалога держим в памяти процесса (разговор длится минуты; перезапуск
сервиса его обнулит — это ок). Каждый ход продюсера — строгий JSON.
"""
import threading
import time
import uuid

from . import agent_runner
from .integrations import openai_api, openclaw_cli

# ключи брифа — ДОЛЖНЫ совпадать с m1_idea.BRIEF_KEYS (+ свободные «details»)
BRIEF_KEYS = ("idea", "tone", "hero", "core_conflict", "hook_type",
              "target_emotion", "visual_mood", "series_link")

_SYSTEM = """Ты — опытный РЕЖИССЁР коротких вертикальных видео-драм (9:16, \
~30 секунд, реплики героев на казахском, аудитория — женщины 30+). Ты лично, \
ГЛУБОКО и дотошно расспрашиваешь автора про ЕЁ идею, прежде чем команда начнёт \
делать серию. Автор — главный человек: твоя задача — вытащить и понять ЕЁ \
замысел, а НЕ навязать свой.

❗Не приплетай свою тему. Если автор НЕ говорит про люстру/свет/какой-то предмет — \
не упоминай его. Если автор что-то назвала (долг, свекровь, измена, люстра) — \
углубись именно в это, переспроси конкретику.

Веди диалог на русском, тепло и по-человечески. За один ход — 1–3 связанных \
вопроса (не вываливай всё разом). Дотошно, деталь за деталью, выясни:
- про что история и чего хочет автор (её идея, а не твоя);
- главный герой: имя, возраст, ВНЕШНОСТЬ (как выглядит, одежда), характер;
- другие персонажи в кадре (кто, как выглядят);
- центральный конфликт и что поставлено на карту;
- место и время действия (сеттинг);
- тон и эмоция, которую хотим вызвать у зрителя;
- чем зацепить в первые 3 секунды (хук) и чем оборвать в конце (клиффхэнгер);
- визуальный стиль/настроение;
- подтверди, что реплики героев — на казахском.

Сделай примерно 5–8 обменов (дотошно!), всегда задавай уточняющие вопросы по \
её ответам. Когда деталей действительно достаточно — заверши: своими словами \
перескажи замысел для подтверждения и собери бриф.

ВСЕГДА отвечай СТРОГО валидным JSON одного из двух видов, без markdown и пояснений:
- если ещё спрашиваешь:
  {"done": false, "message": "<твои вопросы автору>"}
- если готов завершить:
  {"done": true, "message": "<короткий пересказ замысла для подтверждения>", \
"brief": {"idea": "<тема>", "tone": "<тон>", "hero": "<герой>", \
"core_conflict": "<конфликт>", "hook_type": "<тип хука>", \
"target_emotion": "<эмоция-цель>", "visual_mood": "<визуал>", \
"series_link": "<связь с сезоном>", "details": "<абзац с конкретикой от автора: \
имена, повороты, сеттинг, концовка, пожелания>"}}
"""

TTL = 60 * 60  # храним сессию час
_sessions: dict[str, dict] = {}
_lock = threading.Lock()


def available() -> bool:
    return agent_runner.llm_available()


def _cleanup() -> None:
    now = time.time()
    with _lock:
        for sid in [s for s, v in _sessions.items() if now - v["ts"] > TTL]:
            _sessions.pop(sid, None)


def _ask(theme: str, history: list[dict]) -> dict:
    """Один ход продюсера. history=[{role:'user'|'producer', text}]. -> {done,message,brief?}"""
    convo = "\n".join(
        ("АВТОР: " if h["role"] == "user" else "ПРОДЮСЕР: ") + h["text"]
        for h in history
    )
    prompt = (
        f"{_SYSTEM}\n\n# ТЕМА ОТ АВТОРА\n{theme or '(не указана — спроси про неё)'}\n\n"
        f"# ДИАЛОГ ПОКА ЧТО\n{convo or '(пусто — задай первый вопрос)'}\n\n"
        "Ответь следующим ходом продюсера в виде JSON."
    )
    raw = openclaw_cli.chat(prompt)
    if not raw:
        raw = openai_api.chat("Ты — продюсер. Отвечай только JSON.", prompt)
    data = agent_runner.parse_json(raw) if raw else None
    if not isinstance(data, dict) or "message" not in data:
        # не разобрали JSON — трактуем ответ как обычный вопрос автору
        fallback = (raw or "Расскажи чуть подробнее о своей идее?").strip()
        return {"done": False, "message": fallback[:1500]}
    data["done"] = bool(data.get("done"))
    return data


def start(theme: str) -> dict:
    _cleanup()
    sid = uuid.uuid4().hex[:12]
    history: list[dict] = []
    if theme:
        history.append({"role": "user", "text": theme})
    turn = _ask(theme, history)
    history.append({"role": "producer", "text": turn["message"]})
    with _lock:
        _sessions[sid] = {"theme": theme, "history": history,
                          "ts": time.time(), "brief": turn.get("brief")}
    return {"session": sid, **turn}


def reply(sid: str, message: str) -> dict | None:
    with _lock:
        s = _sessions.get(sid)
    if not s:
        return None
    s["history"].append({"role": "user", "text": (message or "").strip()[:1000]})
    turn = _ask(s["theme"], s["history"])
    s["history"].append({"role": "producer", "text": turn["message"]})
    s["ts"] = time.time()
    if turn.get("done") and isinstance(turn.get("brief"), dict):
        s["brief"] = turn["brief"]
    return turn


def get_brief(sid: str) -> dict | None:
    with _lock:
        s = _sessions.get(sid)
    return s.get("brief") if s else None


def drop(sid: str) -> None:
    with _lock:
        _sessions.pop(sid, None)
