"""МОДУЛЬ 8 — МОНТАЖ. Склейка клипов + озвучка + karaoke-субтитры → финальный ролик."""
import math
from pathlib import Path

from .. import config, ffmpeg_tool


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    storyboard = ctx["storyboard"]
    video_paths = ctx.get("video_paths", [None] * len(storyboard))
    image_paths = ctx.get("image_paths", [None] * len(storyboard))
    voice_paths = ctx.get("voice_paths", [None] * len(storyboard))

    def _at(lst, idx):
        return lst[idx] if idx < len(lst) else None

    # базовая длительность кадра — чтобы серия укладывалась в ~45–60 сек
    n = max(1, len(storyboard))
    base = ctx.get("scene_secs") or max(3, min(config.SCENE_SECONDS, round(58 / n)))

    # длительность КАЖДОГО кадра: не короче озвучки, иначе реплику обрежет (фикс аудита #2)
    secs_list: list[int] = []
    for i in range(len(storyboard)):
        s = base
        voice = _at(voice_paths, i)
        if voice and Path(voice).exists():
            d = ffmpeg_tool.media_duration(voice)
            if d:
                s = max(base, math.ceil(d + 0.3))   # вместить речь + маленький хвост
        secs_list.append(s)

    scene_clips: list[Path] = []
    for i, shot in enumerate(storyboard):
        out = workdir / f"scene_clip_{i}.mp4"
        v = Path(p) if (p := _at(video_paths, i)) else None
        img = Path(p) if (p := _at(image_paths, i)) else None
        voice = Path(p) if (p := _at(voice_paths, i)) else None
        ffmpeg_tool.make_scene_clip(
            out_path=out,
            seconds=secs_list[i],
            video_src=v,
            image_src=img,
            voice_src=voice,
            caption=shot["voice"],                  # станет karaoke-субтитром
            word_timings=shot.get("word_timings"),  # реальные тайминги, если есть
        )
        scene_clips.append(out)

    # монтажный лист (EDL): реальный тайминг + субтитр на каждый кадр
    edl, t = [], 0.0
    for i, shot in enumerate(storyboard):
        edl.append({
            "id": shot.get("id", i + 1),
            "in": round(t, 1), "out": round(t + secs_list[i], 1),
            "subtitle": shot.get("voice", ""), "sub_style": "karaoke, big, outline, bottom",
            "transition": "hard cut" if shot.get("role") in ("ПОВОРОТ", "КЛИФФХЭНГЕР") else "cut",
        })
        t += secs_list[i]
    total = int(round(t))
    ctx["edl"] = {"duration_total": total,
                  "music": ctx.get("music_mood", "single track"), "timeline": edl}
    ctx["_episode_secs"] = total    # реальная длина — для гейта длины (фикс аудита #5)

    final = config.OUTPUT_DIR / f"{job.id}.mp4"
    ffmpeg_tool.concat_clips(scene_clips, final)
    job.video_path = str(final)
    return (f"Готовый ролик собран: {len(scene_clips)} кадров ≈ {total} сек, "
            f"karaoke-субтитры есть → {final.name}")
