"""Генерация клипов и финальная склейка через ffmpeg (бандл imageio-ffmpeg).

Подписи рисуем через Pillow (бандл-ffmpeg без drawtext) и накладываем
фильтром overlay. Работает в двух режимах:
- реальный контент: на вход дают картинку (Nano Banana) или видео (Veo) + голос;
- демо: ничего нет -> цветной клип с подписью сцены.
На выходе — нормализованные клипы одного формата для безопасной склейки.
"""
import os
import re
import subprocess
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config


def media_duration(path: Path | str) -> float | None:
    """Длительность аудио/видео в секундах через ffmpeg (-i печатает Duration в stderr)."""
    try:
        proc = subprocess.run([config.FFMPEG, "-i", str(path)],
                              capture_output=True, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
        if m:
            h, mn, s = m.groups()
            return int(h) * 3600 + int(mn) * 60 + float(s)
    except Exception:  # noqa: BLE001
        pass
    return None

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


def _layout_words(text: str, font, draw, max_w: float):
    """Перенос слов по строкам с позициями. -> (positions[(word,x,y,w)], box, lines_w)."""
    words = text.split()
    space = draw.textlength(" ", font=font)
    line_h = int(font.size * 1.3) if hasattr(font, "size") else 62
    # жадный перенос
    lines: list[list[str]] = []
    cur: list[str] = []
    cur_w = 0.0
    for w in words:
        ww = draw.textlength(w, font=font)
        add = ww if not cur else cur_w + space + ww
        if cur and add > max_w:
            lines.append(cur)
            cur, cur_w = [w], ww
        else:
            cur.append(w)
            cur_w = add
    if cur:
        lines.append(cur)

    block_h = line_h * len(lines)
    y0 = H - block_h - 240
    positions = []
    widest = 0.0
    y = y0
    for ln in lines:
        lw = sum(draw.textlength(w, font=font) for w in ln) + space * (len(ln) - 1)
        widest = max(widest, lw)
        x = (W - lw) / 2
        for w in ln:
            ww = draw.textlength(w, font=font)
            positions.append((w, x, y, ww))
            x += ww + space
        y += line_h
    pad = 36
    widest = min(widest, W - 2 * pad)
    box = [(W - widest) / 2 - pad, y0 - pad, (W + widest) / 2 + pad, y0 + block_h + pad]
    return positions, box


def _word_windows(n: int, seconds: float, word_timings: list | None):
    """Тайминги подсветки слов. Реальные тайминги (из аудио) или равномерно по длине."""
    if word_timings and len(word_timings) == n:
        return [(float(a), float(b)) for a, b in word_timings]
    return None  # рассчитаем по весам ниже


def _karaoke_pngs(text: str, out_base: Path, seconds: float,
                  word_timings: list | None = None):
    """PNG на каждое слово (текущее подсвечено золотом). -> [(path, t0, t1)] или None."""
    words = text.split()
    n = len(words)
    if n <= 1:
        return None  # одно слово/пусто — обычная статичная подпись
    font = _font(48)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    positions, box = _layout_words(text, font, probe, W - 2 * 60)

    # тайминги: реальные из аудио или пропорционально длине слова
    win = _word_windows(n, seconds, word_timings)
    if win is None:
        weights = [len(w) + 1 for w in words]
        total = sum(weights)
        win, acc = [], 0.0
        for wgt in weights:
            dur = seconds * wgt / total
            win.append((acc, acc + dur))
            acc += dur

    states = []
    for active in range(n):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle(box, fill=(0, 0, 0, 120))
        for i, (w, x, y, _) in enumerate(positions):
            color = (255, 209, 92, 255) if i == active else (245, 245, 245, 255)
            d.text((x, y), w, font=font, fill=color,
                   stroke_width=2, stroke_fill=(0, 0, 0, 200))
        p = out_base.with_suffix(f".kw{active}.png")
        im.save(p)
        states.append((p, win[active][0], win[active][1]))
    return states


def make_scene_clip(
    out_path: Path,
    seconds: int,
    video_src: Path | None = None,
    image_src: Path | None = None,
    voice_src: Path | None = None,
    caption: str = "",
    word_timings: list | None = None,
) -> None:
    """Собирает один нормализованный клип сцены (видео+аудио, W×H, FPS, ровно seconds).

    Субтитр — karaoke (слово-за-словом, подсветка текущего) по editor.md. Если
    слово одно/пусто — обычная статичная подпись. word_timings (если есть) —
    реальные тайминги слов из аудио; иначе раскладываем равномерно по длине.
    """
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

    # подписи: karaoke (несколько PNG) или одна статичная
    states = _karaoke_pngs(caption, out_path, seconds, word_timings) if caption.strip() else None
    caption_pngs: list[Path] = []
    if states:
        captions = states  # [(path, t0, t1)]
    else:
        single = out_path.with_suffix(".cap.png")
        _caption_png(caption or " ", single)
        captions = [(single, None, None)]
    caption_pngs = [c[0] for c in captions]

    # вход на каждую подпись, затем аудио
    cap_inputs: list[str] = []
    for png, _, _ in captions:
        cap_inputs += ["-i", str(png)]
    audio_idx = 1 + len(captions)
    if voice_src and voice_src.exists():
        audio_inputs = ["-i", str(voice_src)]
    else:
        audio_inputs = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]

    # цепочка overlay: каждый PNG поверх предыдущего (для karaoke — с временным окном)
    parts = [bg_chain]
    prev = "[bg]"
    for i, (_png, t0, t1) in enumerate(captions):
        in_label = f"[{i+1}:v]"
        out_label = "[vout]" if i == len(captions) - 1 else f"[v{i}]"
        enable = f":enable='between(t,{t0:.3f},{t1:.3f})'" if t0 is not None else ""
        parts.append(f"{prev}{in_label}overlay=0:0:format=auto{enable}{out_label}")
        prev = out_label
    parts.append(f"[{audio_idx}:a]apad,atrim=0:{seconds},asetpts=PTS-STARTPTS[aout]")
    filtergraph = ";".join(parts)

    try:
        _run([
            *base_inputs,
            *cap_inputs,
            *audio_inputs,
            "-filter_complex", filtergraph,
            "-map", "[vout]", "-map", "[aout]",
            "-t", str(seconds),
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            str(out_path),
        ])
    finally:
        for png in caption_pngs:
            png.unlink(missing_ok=True)


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
