"""Хранилище задач конвейера (in-memory + на диск) и модель статусов."""
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config

# Состояние задач храним ВНЕ output/ (иначе утекло бы в /media).
STATE_DIR = config.BASE_DIR / ".state" / "jobs"
STATE_DIR.mkdir(parents=True, exist_ok=True)

# Названия модулей конвейера (должно совпадать с pipeline.MODULES по длине/порядку)
MODULE_NAMES = [
    "ИДЕЯ", "СЦЕНАРИЙ", "КАСТИНГ", "РАСКАДРОВКА", "ГЕРОЙ", "КАРТИНКИ", "АНИМАЦИЯ",
    "ЗВУК", "МОНТАЖ", "КОНТРОЛЬ", "ПРИЁМКА", "АНАЛИТИК", "ПУБЛИКАЦИЯ",
]

# поля контекста, которые безопасно отдавать наружу / сохранять
_SAFE_CTX_KEYS = ("idea", "brief", "brief_locked", "cast", "cast_confirmed", "scenes",
                  "storyboard", "voice_plan", "qc", "qc_log", "review", "forecast",
                  "publish", "edl")


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
    status: str = "queued"       # queued | running | awaiting_cast | done | error
    modules: list[ModuleState] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    video_path: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    pause_index: int = 0          # с какого модуля продолжить после паузы (кастинг)
    series_id: str = ""           # сериал (общий для всех серий); по умолчанию = свой id
    episode: int = 1              # номер серии в сезоне

    def public(self) -> dict:
        """Безопасное представление для фронта. Строим вручную (без asdict —
        в context лежат Path/lambda и его меняет фоновый поток)."""
        ctx = self.context
        return {
            "id": self.id,
            "theme": self.theme,
            "status": self.status,
            "error": self.error,
            "created_at": self.created_at,
            "series_id": self.series_id or self.id,
            "episode": self.episode,
            "modules": [
                {"name": m.name, "status": m.status, "detail": m.detail}
                for m in self.modules
            ],
            "context": {k: ctx.get(k) for k in _SAFE_CTX_KEYS},
            "has_video": bool(self.video_path),
            "media": self._media(),
            "progress": (round(sum(1 for m in self.modules if m.status == "done")
                               / len(self.modules) * 100) if self.modules else 0),
        }

    def _media(self) -> dict:
        """Ссылки на сгенерированные кадры/клипы (для превью)."""
        folder = config.OUTPUT_DIR / self.id
        base = f"/media/{self.id}"
        media: dict[str, Any] = {"hero": None, "model_sheet": None,
                                 "chars": [], "scenes": [], "clips": []}

        def _num(p: Path) -> int:
            # числовая сортировка: scene_2 < scene_10 (а не лексикографическая)
            try:
                return int(p.stem.split("_")[-1])
            except ValueError:
                return 0

        if folder.is_dir():
            if (folder / "hero.png").exists():
                media["hero"] = f"{base}/hero.png"
            if (folder / "model_sheet.png").exists():
                media["model_sheet"] = f"{base}/model_sheet.png"
            media["chars"] = [f"{base}/{p.name}" for p in
                              sorted(folder.glob("char_*.png"))]
            media["scenes"] = [f"{base}/{p.name}" for p in
                               sorted(folder.glob("scene_*.png"), key=_num)]
            media["clips"] = [f"{base}/{p.name}" for p in
                              sorted(folder.glob("clip_*.mp4"), key=_num)]
        media["video"] = f"/api/jobs/{self.id}/video" if self.video_path else None
        return media


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.RLock()
        self._load()

    def create(self, theme: str, series_id: str = "", episode: int = 1) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], theme=theme,
                  modules=[ModuleState(name=n) for n in MODULE_NAMES],
                  episode=episode)
        job.series_id = series_id or job.id   # новый сериал = свой id
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

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.status in ("queued", "running"))

    # --- персистентность ---
    def save(self, job: Job) -> None:
        with self._lock:
            ctx = job.context
            wd = ctx.get("workdir")
            data = {
                "id": job.id, "theme": job.theme, "status": job.status,
                "error": job.error, "video_path": job.video_path,
                "created_at": job.created_at, "workdir": str(wd) if wd else None,
                "pause_index": job.pause_index,
                "series_id": job.series_id, "episode": job.episode,
                "modules": [{"name": m.name, "status": m.status, "detail": m.detail}
                            for m in job.modules],
                "context": {k: ctx.get(k) for k in _SAFE_CTX_KEYS},
            }
            try:
                (STATE_DIR / f"{job.id}.json").write_text(
                    json.dumps(data, ensure_ascii=False), encoding="utf-8")
            except Exception as e:  # noqa: BLE001
                print(f"[jobs] save error: {e}", flush=True)

    def _load(self) -> None:
        for f in STATE_DIR.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            modules = [ModuleState(**m) for m in d.get("modules", [])]
            status = d.get("status", "done")
            if status in ("queued", "running"):   # прервано падением сервиса
                status = "error"
                d["error"] = d.get("error") or "прервано (сервис перезапускался)"
                for m in modules:
                    if m.status == "running":
                        m.status, m.detail = "error", (m.detail or "прервано перезапуском")
            job = Job(id=d["id"], theme=d.get("theme", ""), status=status,
                      modules=modules, video_path=d.get("video_path"),
                      error=d.get("error"), created_at=d.get("created_at", time.time()),
                      pause_index=d.get("pause_index", 0),
                      episode=d.get("episode", 1))
            job.series_id = d.get("series_id") or d["id"]
            job.context = d.get("context") or {}
            if d.get("workdir"):
                job.context["workdir"] = Path(d["workdir"])
            self._jobs[job.id] = job


store = JobStore()
