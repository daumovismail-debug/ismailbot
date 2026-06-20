"""МОДУЛЬ 9 — КОНТРОЛЬ. Финальная проверка качества (по controller.md).

Базовые проверки (всегда): все кадры на месте, есть финал, длина 45–60.
Vision-сверка (если есть OpenClaw): каждый выборочный кадр сравнивается с эталоном
ТОГО персонажа, что в этом кадре (по storyboard.references), с тип-зависимым порогом
(люди — строже, не-люди вроде кота — мягче). Так лочим не только героиню.
"""
from pathlib import Path

from .. import config
from ..integrations import openclaw_cli

THR_HUMAN = 0.60
THR_OTHER = 0.55   # животные/объекты: консистентность мягче (vision, не ArcFace)


def run(job, ctx: dict) -> str:
    storyboard = ctx.get("storyboard", [])
    image_paths = ctx.get("image_paths", [None] * len(storyboard))
    workdir = ctx.get("workdir")
    cast = ctx.get("cast", [])
    type_by_id = {c.get("id"): c.get("type", "human") for c in cast}

    have = sum(1 for p in image_paths if p and Path(p).exists())
    total = len(storyboard)
    expect_real = config.HAS_OPENCLAW or config.HAS_OPENAI
    issues = []
    if expect_real and have < total:
        issues.append(f"нет картинок: {total - have}/{total}")
    if not (job.video_path and Path(job.video_path).exists()):
        issues.append("нет финального видео")

    secs = int(ctx.get("_episode_secs", 0))
    if secs and not (40 <= secs <= 62):
        issues.append(f"длина {secs}с вне 45–60")

    def _ref(cid: str):
        if not workdir:
            return None
        name = "hero.png" if cid == "heroine" else f"char_{cid}.png"
        p = Path(workdir) / name
        return str(p) if p.exists() else None

    # vision-сверка облика по персонажу кадра (выборка: начало/середина/конец)
    checked: list[tuple[str, float]] = []
    if openclaw_cli.available() and workdir and total:
        for i in dict.fromkeys([0, total // 2, total - 1]):   # уникальные индексы
            if i >= len(image_paths):
                continue
            p = image_paths[i]
            if not (p and Path(p).exists()):
                continue
            cid = (storyboard[i].get("references") or ["heroine"])[0]
            rp = _ref(cid)
            if not rp:
                continue
            fm = openclaw_cli.compare_faces(rp, p)
            if fm is not None:
                checked.append((cid, fm))
        bad = [(cid, fm) for cid, fm in checked
               if fm < (THR_HUMAN if type_by_id.get(cid, "human") == "human" else THR_OTHER)]
        if bad:
            who = ", ".join(cid for cid, _ in bad)
            issues.append(f"облик «уплыл» у {who} ({len(bad)} из {len(checked)})")

    avg_fm = round(sum(f for _, f in checked) / len(checked), 2) if checked else None
    ctx["qc"] = {"frames_ok": have, "frames_total": total,
                 "demo": not expect_real, "face_match_avg": avg_fm,
                 "checked": len(checked), "issues": issues}

    vision = (f"vision: облик avg {avg_fm} ({len(checked)} кадра)" if avg_fm is not None
              else ("vision готов (нет кадров для сверки)" if openclaw_cli.available()
                    else "vision выкл (демо)"))
    if issues:
        return f"Контроль: ⚠️ {', '.join(issues)}. {vision}"
    if not expect_real:
        return f"Контроль: ✅ демо (плейсхолдеры), видео собрано, длина в норме. {vision}"
    return f"Контроль: ✅ проверки пройдены ({have}/{total} кадров, видео есть). {vision}"
