"""FastAPI: REST API конвейера + раздача веб-панели."""
import os
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, idea_bank
from .jobs import store
from .pipeline import run_pipeline

app = FastAPI(title="СВЕТ — фабрика видео")

# не даём перегрузить слабый сервер десятками параллельных рендеров
MAX_ACTIVE_JOBS = int(os.getenv("MAX_ACTIVE_JOBS", "2"))


class CreateJob(BaseModel):
    theme: str | None = None


class CastUpdate(BaseModel):
    cast: list | None = None   # отредактированная каста; None = принять как есть


@app.get("/api/status")
def status():
    """Какие интеграции подключены (режим демо или реальный)."""
    real = (config.HAS_OPENCLAW or config.HAS_OPENAI or config.HAS_XAI
            or config.HAS_POLLINATIONS)
    return {
        "openclaw": config.HAS_OPENCLAW,        # подписка ChatGPT (ТЕКСТ)
        "pollinations": config.HAS_POLLINATIONS,  # бесплатные КАРТИНКИ
        "openai": config.HAS_OPENAI,            # ChatGPT API (запасной)
        "xai": config.HAS_XAI,                  # Grok API (видео)
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
    return FileResponse(str(p), media_type="video/mp4", filename=f"svet_{job_id}.mp4")


# отдаём сгенерированные кадры по публичному URL (нужно Grok'у для image-to-video)
app.mount("/media", StaticFiles(directory=str(config.OUTPUT_DIR)), name="media")

# веб-панель (статика) — монтируем последней, чтобы не перекрывать /api
app.mount("/", StaticFiles(directory=str(config.WEB_DIR), html=True), name="web")
