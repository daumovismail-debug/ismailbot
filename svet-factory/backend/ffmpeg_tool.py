"""Генерация клипов и финальная склейка через ffmpeg (бандл imageio-ffmpeg).

Подписи рисуем через Pillow (бандл-ffmpeg без drawtext) и накладываем
фильтром overlay. Работает в двух режимах:
- реальный контент: на вход дают картинку (Nano Banana) или видео (Veo) + голос;
- демо: ничего нет -> цветной клип с подписью сцены.
На выходе — нормализованные клипы одного формата для безопасной склейки.
"""
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = 30


def _font(size: int):
    """Шрифт DejaVu, а если его нет в системе — встроенный (чтобы не падать)."""
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()

# тёплая палитра под нишу «свет» для демо-клипов
SCENE_COLORS = ["0x2b1d3a", "0x3a2438", "0x1d2b3a", "0x3a2e1d", "0x2a1d2b"]


def _run(args: list[str]) -> None:
    subprocess.run([config.FFMPEG, "-y", "-loglevel", "error", *args], check=True)


def _caption_png(text: str, out_path: Path, title: bool = False) -> None:
    """Рисует подпись на прозрачном холсте W×H (текст у нижней трети)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    size = 84 if title else 48
    font = _font(size)

    wrapped = textwrap.fill(text, width=20 if title else 26)
    lines = wrapped.split("\n")
    line_h = int(size * 1.3)
    block_h = line_h * len(lines)

    y0 = H // 2 - block_h // 2 if title else H - block_h - 240
    pad = 36
    # ширина плашки по самой длинной строке (но не шире кадра)
    max_w = max(draw.textlength(l, font=font) for l in lines)
    max_w = min(max_w, W - 2 * pad)
    box = [
        (W - max_w) / 2 - pad, y0 - pad,
        (W + max_w) / 2 + pad, y0 + block_h + pad,
    ]
    draw.rectangle(box, fill=(0, 0, 0, 120))

    y = y0
    for line in lines:
        lw = draw.textlength(line, font=font)
        draw.text(((W - lw) / 2, y), line, font=font, fill=(255, 255, 255, 255),
                  stroke_width=2, stroke_fill=(0, 0, 0, 200))
        y += line_h
    img.save(out_path)


def make_scene_clip(
    out_path: Path,
    seconds: int,
    video_src: Path | None = None,
    image_src: Path | None = None,
    voice_src: Path | None = None,
    caption: str = "",
) -> None:
    """Собирает один нормализованный клип сцены (видео+аудио, W×H, FPS, ровно seconds)."""
    tmp_caption = out_path.with_suffix(".cap.png")
    _caption_png(caption or " ", tmp_caption)

    # вход 0 — фон (видео / картинка / цвет)
    if video_src and video_src.exists():
        base_inputs = ["-i", str(video_src)]
        bg_chain = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
                    f"crop={W}:{H},setsar=1,fps={FPS},format=yuv420p[bg]")
    elif image_src and image_src.exists():
        base_inputs = ["-loop", "1", "-t", str(seconds), "-i", str(image_src)]
        bg_chain = (
            f"[0:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
            f"crop={W*2}:{H*2},"
            f"zoompan=z='min(zoom+0.0008,1.15)':d={seconds*FPS}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
            f"setsar=1,format=yuv420p[bg]"
        )
    else:
        color = SCENE_COLORS[(seconds + len(caption)) % len(SCENE_COLORS)]
        base_inputs = ["-f", "lavfi", "-t", str(seconds),
                       "-i", f"color=c={color}:s={W}x{H}:r={FPS}"]
        bg_chain = "[0:v]format=yuv420p[bg]"

    # вход 1 — подпись, вход 2 — аудио
    if voice_src and voice_src.exists():
        audio_inputs = ["-i", str(voice_src)]
    else:
        audio_inputs = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]

    filtergraph = (
        f"{bg_chain};"
        f"[bg][1:v]overlay=0:0:format=auto[vout];"
        f"[2:a]apad,atrim=0:{seconds},asetpts=PTS-STARTPTS[aout]"
    )

    _run([
        *base_inputs,
        "-i", str(tmp_caption),
        *audio_inputs,
        "-filter_complex", filtergraph,
        "-map", "[vout]", "-map", "[aout]",
        "-t", str(seconds),
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        str(out_path),
    ])
    tmp_caption.unlink(missing_ok=True)


def concat_clips(clips: list[Path], out_path: Path) -> None:
    """Склейка нормализованных клипов через concat demuxer."""
    clips = [c for c in clips if c and Path(c).exists()]
    if not clips:
        raise RuntimeError("нет клипов для склейки")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for c in clips:
            f.write(f"file '{c.resolve()}'\n")
        listfile = f.name
    try:
        _run([
            "-f", "concat", "-safe", "0", "-i", listfile,
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            str(out_path),
        ])
    finally:
        os.unlink(listfile)


def make_placeholder_image(out_path: Path, caption: str) -> None:
    """Демо-картинка героя/сцены (когда нет Nano Banana) — рисуется через Pillow."""
    base = Image.new("RGBA", (W, H), (43, 29, 58, 255))
    cap = out_path.with_suffix(".cap.png")
    _caption_png(caption, cap, title=True)
    with Image.open(cap) as overlay:
        base.alpha_composite(overlay.convert("RGBA"))
    base.convert("RGB").save(out_path)
    cap.unlink(missing_ok=True)
