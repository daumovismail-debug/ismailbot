"""МОДУЛЬ 8 — МОНТАЖ. Склейка клипов + озвучка + подписи → финальный ролик."""
from pathlib import Path

from .. import config, ffmpeg_tool


def run(job, ctx: dict) -> str:
    workdir: Path = ctx["workdir"]
    storyboard = ctx["storyboard"]
    video_paths = ctx.get("video_paths", [None] * len(storyboard))
    image_paths = ctx.get("image_paths", [None] * len(storyboard))
    voice_paths = ctx.get("voice_paths", [None] * len(storyboard))

    scene_clips: list[Path] = []
    # длительность кадра подгоняем так, чтобы вся серия укладывалась в 45–60 сек
    n = max(1, len(storyboard))
    secs = max(3, min(config.SCENE_SECONDS, round(58 / n)))
    for i, shot in enumerate(storyboard):
        out = workdir / f"scene_clip_{i}.mp4"
        v = Path(video_paths[i]) if video_paths[i] else None
        img = Path(image_paths[i]) if image_paths[i] else None
        voice = Path(voice_paths[i]) if voice_paths[i] else None
        # подпись = реплика (станет субтитром поверх кадра)
        ffmpeg_tool.make_scene_clip(
            out_path=out,
            seconds=secs,
            video_src=v,
            image_src=img,
            voice_src=voice,
            caption=shot["voice"],
        )
        scene_clips.append(out)

    final = config.OUTPUT_DIR / f"{job.id}.mp4"
    ffmpeg_tool.concat_clips(scene_clips, final)
    job.video_path = str(final)
    total = secs * len(scene_clips)
    return f"Готовый ролик собран: {len(scene_clips)} кадров × {secs}с ≈ {total} сек → {final.name}"
