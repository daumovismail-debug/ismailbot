"""МОДУЛЬ 7 — ЗВУК / ГОЛОС (по voice.md).

Строит план озвучки: реплика на казахском (voice_kz) на каждый кадр + голос
персонажа (voice_id) + музыка (1 трек на серию). Если есть ключ ElevenLabs —
синтезирует; иначе план записан, аудио добавим, когда подключим казахский движок.
"""
from pathlib import Path

from ..integrations import elevenlabs


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    scenes = ctx.get("scenes", [])

    plan = []
    voice_paths: list[str | None] = []
    real = 0
    for i, s in enumerate(scenes):
        line_kz = s.get("voice_kz") or ""        # казахский (если Сценарист дал)
        line = line_kz or s.get("voice", "")
        plan.append({"id": s.get("id", i + 1), "voice_kz": line_kz,
                     "voice_ru": s.get("voice", "")})
        audio = elevenlabs.tts(line) if line else None
        if audio:
            p = workdir / f"voice_{i}.mp3"
            p.write_bytes(audio)
            voice_paths.append(str(p))
            real += 1
        else:
            voice_paths.append(None)

    ctx["voice_plan"] = plan
    ctx["voice_paths"] = voice_paths
    ctx["music_mood"] = "tense dramatic, single track, build to cliffhanger"

    have_kz = any(p["voice_kz"] for p in plan)
    if real:
        return f"Озвучено реплик: {real}/{len(scenes)} (ElevenLabs)"
    note = "план озвучки готов (казахский)" if have_kz else "план озвучки готов"
    return f"Звук: {note}; аудио — когда подключим казахский движок (демо: без звука)"
