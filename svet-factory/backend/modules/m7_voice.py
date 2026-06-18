"""МОДУЛЬ 7 — ЗВУК. Озвучка реплик каждой сцены (ElevenLabs)."""
from pathlib import Path

from ..integrations import elevenlabs


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    storyboard = ctx["storyboard"]

    voice_paths: list[str | None] = []
    real = 0
    for i, shot in enumerate(storyboard):
        audio = elevenlabs.tts(shot["voice"])
        if audio:
            p = workdir / f"voice_{i}.mp3"
            p.write_bytes(audio)
            voice_paths.append(str(p))
            real += 1
        else:
            voice_paths.append(None)  # сцена будет с тишиной

    ctx["voice_paths"] = voice_paths
    if real:
        return f"Озвучено реплик: {real}/{len(storyboard)} (ElevenLabs)"
    return "Звук: демо-режим — без озвучки (нет ключа ElevenLabs)"
