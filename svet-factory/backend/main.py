"""FastAPI: REST API конвейера + раздача веб-панели."""
import os
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask

from . import cleanup, config, idea_bank, interview
from .jobs import store
from .pipeline import run_pipeline

app = FastAPI(title="СВЕТ — фабрика видео")

# не даём перегрузить слабый сервер десятками параллельных рендеров
MAX_ACTIVE_JOBS = int(os.getenv("MAX_ACTIVE_JOBS", "2"))


class CreateJob(BaseModel):
    theme: str | None = None


class CastUpdate(BaseModel):
    cast: list | None = None   # отредактированная каста; None = принять как есть


class InterviewStart(BaseModel):
    theme: str | None = None


class InterviewReply(BaseModel):
    session: str
    message: str | None = None


class InterviewConfirm(BaseModel):
    session: str
    brief: dict | None = None   # ручные правки брифа; None = взять из сессии


@app.get("/api/status")
def status():
    """Какие интеграции подключены (режим демо или реальный)."""
    real = (config.HAS_OPENCLAW or config.HAS_OPENAI or config.HAS_XAI
            or config.HAS_POLLINATIONS)
    return {
        "openclaw": config.HAS_OPENCLAW,        # подписка ChatGPT (ТЕКСТ)
        "pollinations": config.HAS_POLLINATIONS,  # бесплатные КАРТИНКИ
        "grok_images": config.USE_GROK_IMAGES,    # Grok рисует картинки (подписка)
        "grok_browser": config.USE_GROK_BROWSER,  # Grok делает видео (подписка)
        "openai": config.HAS_OPENAI,            # ChatGPT API (запасной)
        "xai": config.HAS_XAI,                  # Grok API (видео)
        "voice": config.HAS_VOICE,              # казахский голос (edge-tts, бесплатно)
        "elevenlabs": config.HAS_ELEVENLABS,
        "mode": "real" if real else "demo",
    }


@app.get("/api/ideas")
def ideas():
    return idea_bank.IDEA_BANK


@app.post("/api/jobs")
def create_job(body: CreateJob):
    if store.active_count() >= MAX_ACTIVE_JOBS:
        raise HTTPException(429, f"занято: уже {MAX_ACTIVE_JOBS} активных задач, подожди")
    job = store.create((body.theme or "").strip()[:200])
    threading.Thread(target=run_pipeline, args=(job,), daemon=True).start()
    return {"id": job.id}


@app.post("/api/interview/start")
def interview_start(body: InterviewStart):
    """Запускает интервью с продюсером (он первым задаёт вопросы автору)."""
    return interview.start((body.theme or "").strip()[:200])


@app.post("/api/interview/reply")
def interview_reply(body: InterviewReply):
    """Ответ автора продюсеру → следующий вопрос или готовый бриф (done=true)."""
    out = interview.reply(body.session, body.message or "")
    if out is None:
        raise HTTPException(404, "сессия интервью не найдена (начни заново)")
    return out


@app.post("/api/interview/confirm")
def interview_confirm(body: InterviewConfirm):
    """Автор подтвердил замысел → создаём серию с этим брифом и запускаем конвейер."""
    if store.active_count() >= MAX_ACTIVE_JOBS:
        raise HTTPException(429, f"занято: уже {MAX_ACTIVE_JOBS} активных задач, подожди")
    brief = body.brief if isinstance(body.brief, dict) else interview.get_brief(body.session)
    if not isinstance(brief, dict) or not brief:
        raise HTTPException(400, "бриф ещё не готов — продолжи интервью")
    theme = (str(brief.get("idea") or "").strip() or "Серия")[:200]
    job = store.create(theme)
    job.context["brief"] = brief
    job.context["brief_locked"] = True      # m1_idea возьмёт этот бриф как есть
    store.save(job)
    threading.Thread(target=run_pipeline, args=(job,), daemon=True).start()
    interview.drop(body.session)
    return {"id": job.id}


@app.get("/api/jobs")
def list_jobs():
    return [j.public() for j in store.all()]


@app.post("/api/jobs/{job_id}/cast")
def confirm_cast(job_id: str, body: CastUpdate):
    """Подтвердить/поправить касту и продолжить конвейер после паузы кастинга."""
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job.status != "awaiting_cast":
        raise HTTPException(409, "задача не ждёт подтверждения касты")
    if body.cast is not None:
        job.context["cast"] = body.cast        # ручные правки
    job.context["cast_confirmed"] = True        # «пусть решит сам» = принять как есть
    job.status = "running"
    store.save(job)
    threading.Thread(target=run_pipeline, args=(job, job.pause_index), daemon=True).start()
    return {"ok": True}


@app.post("/api/jobs/{job_id}/sequel")
def make_sequel(job_id: str):
    """Создать СЛЕДУЮЩУЮ серию сезона — продолжение от клиффхэнгера прошлой.

    Каста и эталоны переиспользуются (та же героиня/персонажи) — консистентность
    между сериями. Шаг кастинга пропускается (cast_confirmed).
    """
    prev = store.get(job_id)
    if not prev:
        raise HTTPException(404, "job not found")
    if store.active_count() >= MAX_ACTIVE_JOBS:
        raise HTTPException(429, f"занято: уже {MAX_ACTIVE_JOBS} активных задач, подожди")
    scenes = prev.context.get("scenes") or []
    cliff = ""
    if scenes:
        last = scenes[-1]
        cliff = last.get("voice_ru") or last.get("voice", "")

    job = store.create(prev.theme, series_id=prev.series_id or prev.id,
                       episode=prev.episode + 1)
    job.context["prev_cliffhanger"] = cliff
    job.context["prev_theme"] = prev.theme
    # переиспользуем касту прошлой серии (без повторного кастинга)
    if prev.context.get("cast"):
        job.context["cast"] = prev.context["cast"]
        job.context["cast_confirmed"] = True
    store.save(job)
    threading.Thread(target=run_pipeline, args=(job,), daemon=True).start()
    return {"id": job.id, "episode": job.episode}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job.public()


@app.get("/api/jobs/{job_id}/video")
def get_video(job_id: str):
    job = store.get(job_id)
    if not job or not job.video_path:
        raise HTTPException(404, "video not ready")
    # путь должен быть внутри OUTPUT_DIR (защита от выхода за пределы)
    p = Path(job.video_path).resolve()
    if not p.is_file() or not p.is_relative_to(config.OUTPUT_DIR.resolve()):
        raise HTTPException(404, "video not found")
    # после успешной отдачи файла — чистим кадры/видео с диска (экономим место)
    task = BackgroundTask(cleanup.cleanup_job_media, job) \
        if config.AUTO_CLEANUP_AFTER_DOWNLOAD else None
    return FileResponse(str(p), media_type="video/mp4",
                        filename=f"svet_{job_id}.mp4", background=task)


# отдаём сгенерированные кадры по публичному URL (нужно Grok'у для image-to-video)
app.mount("/media", StaticFiles(directory=str(config.OUTPUT_DIR)), name="media")

# веб-панель (статика) — монтируем последней, чтобы не перекрывать /api
app.mount("/", StaticFiles(directory=str(config.WEB_DIR), html=True), name="web")
