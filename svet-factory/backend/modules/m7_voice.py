"""МОДУЛЬ 7 — ЗВУК / ГОЛОС (по voice.md).

Озвучивает реплики на КАЗАХСКОМ бесплатно через edge-tts (нейроголоса Microsoft
Edge). Запасной путь — ElevenLabs (если есть ключ). Сохраняет mp3 на кадр и кладёт
тайминги слов в storyboard — для точного karaoke-синхрона субтитров в монтаже.
"""
from pathlib import Path

from ..integrations import edge_voice, elevenlabs


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    scenes = ctx.get("scenes", [])
    storyboard = ctx.get("storyboard", [])

    plan = []
    voice_paths: list[str | None] = []
    real = 0
    engine = "—"
    for i, s in enumerate(scenes):
        line_kz = s.get("voice_kz") or ""          # казахский (озвучиваем его)
        line = line_kz or s.get("voice", "")
        plan.append({"id": s.get("id", i + 1), "voice_kz": line_kz,
                     "voice_ru": s.get("voice_ru", "")})

        audio, words = (None, None)
        if line:
            audio, words = edge_voice.tts(line)    # казахский бесплатно
            if audio:
                engine = "edge-tts (KZ)"
            else:
                audio = elevenlabs.tts(line)        # запасной (если ключ)
                if audio:
                    engine = "ElevenLabs"

        if audio:
            p = workdir / f"voice_{i}.mp3"
            p.write_bytes(audio)
            voice_paths.append(str(p))
            real += 1
            # реальные тайминги слов -> точный karaoke-синхрон в монтаже
            if words and i < len(storyboard):
                storyboard[i]["word_timings"] = words
        else:
            voice_paths.append(None)

    ctx["voice_plan"] = plan
    ctx["voice_paths"] = voice_paths
    ctx["music_mood"] = "tense dramatic, single track, build to cliffhanger"

    have_kz = any(p["voice_kz"] for p in plan)
    if real:
        return (f"Озвучено реплик: {real}/{len(scenes)} ({engine}); "
                "karaoke-тайминги по словам есть")
    note = "план озвучки готов (казахский)" if have_kz else "план озвучки готов"
    return f"Звук: {note}; аудио — нет голосового движка (демо: без звука)"
