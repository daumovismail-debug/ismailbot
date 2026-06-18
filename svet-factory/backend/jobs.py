"""Хранилище задач конвейера (in-memory + на диск) и модель статусов."""
import json
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

from . import config

# куда сохраняем задачи, чтобы они пережили перезапуск сервиса
JOBS_DIR = config.OUTPUT_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# Названия 8 модулей в порядке прохождения
MODULE_NAMES = [
    "ИДЕЯ",
    "СЦЕНАРИЙ",
    "РАСКАДРОВКА",
    "ГЕРОЙ",
    "КАРТИНКИ",
    "АНИМАЦИЯ",
    "ЗВУК",
    "МОНТАЖ",
]


@dataclass
class ModuleState:
    name: str
    status: str = "pending"      # pending | running | done | error
    detail: str = ""
    started_at: float | None = None
    finished_at: float | None = None


@dataclass
class Job:
    id: str
    theme: str
    status: str = "queued"       # queued | running | done | error
    modules: list[ModuleState] = field(default_factory=list)
    # промежуточные результаты модулей
    context: dict[str, Any] = field(default_factory=dict)
    video_path: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)

    def public(self) -> dict:
        """Безопасное представление для фронта (без сырых байтов)."""
        d = asdict(self)
        ctx = d.get("context", {})
        # не отдаём наружу большие/бинарные поля
        safe_ctx = {
            "idea": ctx.get("idea"),
            "scenes": ctx.get("scenes"),
            "storyboard": ctx.get("storyboard"),
        }
        d["context"] = safe_ctx
        d["has_video"] = bool(self.video_path)
        return d


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._load()

    def create(self, theme: str) -> Job:
        job = Job(
            id=uuid.uuid4().hex[:12],
            theme=theme,
            modules=[ModuleState(name=n) for n in MODULE_NAMES],
        )
        with self._lock:
            self._jobs[job.id] = job
        self.save(job)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def all(self) -> list[Job]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    # --- персистентность ---
    def save(self, job: Job) -> None:
        """Пишем состояние задачи на диск (переживает перезапуск сервиса)."""
        data = {
            "id": job.id,
            "theme": job.theme,
            "status": job.status,
            "error": job.error,
            "video_path": job.video_path,
            "created_at": job.created_at,
            "modules": [
                {"name": m.name, "status": m.status, "detail": m.detail}
                for m in job.modules
            ],
            "context": {k: job.context.get(k) for k in ("idea", "scenes", "storyboard")},
        }
        try:
            (JOBS_DIR / f"{job.id}.json").write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:  # noqa: BLE001
            print(f"[jobs] save error: {e}", flush=True)

    def _load(self) -> None:
        for f in JOBS_DIR.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            modules = [ModuleState(**m) for m in d.get("modules", [])]
            status = d.get("status", "done")
            # задача, прерванная падением сервиса, помечается как ошибка
            if status in ("queued", "running"):
                status = "error"
                d["error"] = d.get("error") or "прервано (сервис перезапускался)"
                for m in modules:
                    if m.status == "running":
                        m.status = "error"
                        m.detail = m.detail or "прервано перезапуском сервиса"
            job = Job(
                id=d["id"],
                theme=d.get("theme", ""),
                status=status,
                modules=modules,
                video_path=d.get("video_path"),
                error=d.get("error"),
                created_at=d.get("created_at", time.time()),
            )
            job.context = d.get("context") or {}
            self._jobs[job.id] = job


store = JobStore()
