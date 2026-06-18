"""FastAPI: REST API конвейера + раздача веб-панели."""
import threading

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, idea_bank
from .jobs import store
from .pipeline import run_pipeline

app = FastAPI(title="СВЕТ — фабрика видео")


class CreateJob(BaseModel):
    theme: str | None = None


@app.get("/api/status")
def status():
    """Какие интеграции подключены (режим демо или реальный)."""
    return {
        "gemini": config.HAS_GEMINI,
        "elevenlabs": config.HAS_ELEVENLABS,
        "mode": "real" if config.HAS_GEMINI else "demo",
    }


@app.get("/api/ideas")
def ideas():
    return idea_bank.IDEA_BANK


@app.post("/api/jobs")
def create_job(body: CreateJob):
    job = store.create(body.theme or "")
    threading.Thread(target=run_pipeline, args=(job,), daemon=True).start()
    return {"id": job.id}


@app.get("/api/jobs")
def list_jobs():
    return [j.public() for j in store.all()]


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
    return FileResponse(job.video_path, media_type="video/mp4", filename=f"svet_{job_id}.mp4")


# веб-панель (статика) — монтируем последней, чтобы не перекрывать /api
app.mount("/", StaticFiles(directory=str(config.WEB_DIR), html=True), name="web")
