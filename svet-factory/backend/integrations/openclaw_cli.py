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


# путь от LLM читаем, только если он внутри разрешённых папок (защита от чтения
# произвольных файлов вроде /etc/...). OpenClaw кладёт картинки под ~/.openclaw.
_ALLOWED_ROOTS = [Path.home().resolve(), config.OUTPUT_DIR.resolve(),
                  Path("/tmp").resolve()]


def _safe_file(path: str) -> Path | None:
    try:
        p = Path(path).resolve()
    except Exception:  # noqa: BLE001
        return None
    if p.is_file() and any(p.is_relative_to(r) for r in _ALLOWED_ROOTS):
        return p
    _log(f"путь вне разрешённых папок, пропуск: {path}")
    return None


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


def compare_faces(ref_path: str, img_path: str, timeout: int = 120) -> float | None:
    """Vision-сверка: тот же ли персонаж на кадре, что и на эталоне. -> 0..1 или None.

    Просим агента открыть оба файла и вернуть face_match. Работает на сервере, где
    OpenClaw имеет доступ к файлам. Best-effort.
    """
    if not available():
        return None
    msg = (
        f"Open these two image files and compare the MAIN character:\n"
        f"REFERENCE: {ref_path}\nNEW: {img_path}\n"
        "Is it the same character (face, hair, outfit)? Reply ONLY JSON: "
        '{"face_match":0.0-1.0,"same":true/false}'
    )
    out = _run_agent(msg, timeout, session_key=None)
    if not out:
        return None
    m = re.search(r'"face_match"\s*:\s*([01](?:\.\d+)?|\.\d+)', out)
    return float(m.group(1)) if m else None


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
    safe = _safe_file(path) if path else None
    if safe:
        return safe.read_bytes()
    _log("image: file not found / unsafe path in agent reply")
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
    safe = _safe_file(path) if path else None
    if safe:
        return safe.read_bytes()
    _log("video: file not found / unsafe path in agent reply")
    return None
