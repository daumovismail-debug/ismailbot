"""Хранилище задач конвейера (in-memory) и модель статусов."""
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

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

    def create(self, theme: str) -> Job:
        job = Job(
            id=uuid.uuid4().hex[:12],
            theme=theme,
            modules=[ModuleState(name=n) for n in MODULE_NAMES],
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def all(self) -> list[Job]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)


store = JobStore()
