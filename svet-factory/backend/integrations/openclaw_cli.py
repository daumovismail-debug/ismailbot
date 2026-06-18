"""OpenClaw CLI — генерация картинок и видео под подпиской (ChatGPT/Grok).

Зовём `openclaw agent --json` одним запросом, агент генерит файл локально
(через инструменты image_generate / video_generate) и возвращает путь к нему.
Поскольку OpenClaw на том же сервере, мы просто читаем готовый файл с диска.

Всё best-effort: при любой проблеме возвращаем None -> работает запасной движок
или демо-плейсхолдер.
"""
import json
import re
import subprocess
from pathlib import Path

from .. import config

_PNG = re.compile(r"(/\S+?\.png)")
_VID = re.compile(r"(/\S+?\.(?:mp4|mov|webm))")


def _log(msg: str) -> None:
    print(f"[openclaw] {msg}", flush=True)


def available() -> bool:
    return config.USE_OPENCLAW and bool(config.OPENCLAW_BIN)


def _run_agent(message: str, timeout: int, session_key: str | None) -> str | None:
    """Один headless-запрос к агенту OpenClaw, возвращает stdout."""
    cmd = [
        config.OPENCLAW_BIN, "agent",
        "--agent", config.OPENCLAW_AGENT,
        "--json", "--timeout", str(timeout),
    ]
    if session_key:
        cmd += ["--session-key", session_key]
    cmd += ["-m", message]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 120)
        if proc.returncode != 0:
            _log(f"agent rc={proc.returncode}: {proc.stderr[:300]}")
        return proc.stdout
    except Exception as e:  # noqa: BLE001
        _log(f"run error: {e}")
        return None


def _extract_path(stdout: str | None, rx: re.Pattern) -> str | None:
    """Достаём путь к сгенерированному файлу из JSON-ответа агента."""
    if not stdout:
        return None
    try:
        data = json.loads(stdout[stdout.index("{"):])
        result = data.get("result", {})
        for p in result.get("payloads", []):
            for key in ("mediaUrls", "mediaUrl", "text"):
                v = p.get(key)
                if isinstance(v, list) and v:
                    v = v[0]
                if isinstance(v, str):
                    m = rx.search(v)
                    if m:
                        return m.group(1)
        meta = result.get("meta", {})
        for key in ("finalAssistantVisibleText", "finalAssistantRawText"):
            v = meta.get(key)
            if isinstance(v, str):
                m = rx.search(v)
                if m:
                    return m.group(1)
    except Exception:  # noqa: BLE001
        pass
    # запасной вариант — поиск пути по всему выводу
    m = rx.search(stdout)
    return m.group(1) if m else None


def chat(message: str, session_key: str | None = None,
         timeout: int = 180) -> str | None:
    """Текстовый ответ агента (для сценария). Без генерации файлов."""
    if not available():
        return None
    out = _run_agent(message, timeout, session_key)
    if not out:
        return None
    try:
        data = json.loads(out[out.index("{"):])
        result = data.get("result", {})
        meta = result.get("meta", {})
        for key in ("finalAssistantVisibleText", "finalAssistantRawText"):
            if isinstance(meta.get(key), str) and meta[key].strip():
                return meta[key]
        for p in result.get("payloads", []):
            if isinstance(p.get("text"), str) and p["text"].strip():
                return p["text"]
    except Exception:  # noqa: BLE001
        pass
    return out


def generate_image(prompt: str, session_key: str | None = None,
                   timeout: int = 200) -> bytes | None:
    if not available():
        return None
    msg = (
        f"Generate a vertical 9:16 image. {prompt} "
        "After generating, reply with ONLY the absolute file path to the saved "
        ".png file, nothing else."
    )
    path = _extract_path(_run_agent(msg, timeout, session_key), _PNG)
    if path and Path(path).exists():
        return Path(path).read_bytes()
    _log("image: file not found in agent reply")
    return None


def generate_video(prompt: str, image_path: str | None = None,
                   session_key: str | None = None, timeout: int = 480) -> bytes | None:
    if not available():
        return None
    if image_path:
        msg = (
            f"Animate this image into a {config.SCENE_SECONDS}-second vertical 9:16 "
            f"video: {image_path}. Motion: {prompt}. After generating, reply with ONLY "
            "the absolute file path to the saved video file, nothing else."
        )
    else:
        msg = (
            f"Generate a {config.SCENE_SECONDS}-second vertical 9:16 video. {prompt}. "
            "Reply with ONLY the absolute file path to the saved video file, nothing else."
        )
    path = _extract_path(_run_agent(msg, timeout, session_key), _VID)
    if path and Path(path).exists():
        return Path(path).read_bytes()
    _log("video: file not found in agent reply")
    return None
