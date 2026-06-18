"""Оркестратор: гоняет 8 модулей строго по очереди, обновляя статусы задачи."""
import tempfile
import time
import traceback
from pathlib import Path

from .jobs import Job
from .modules import (
    m1_idea,
    m2_script,
    m3_storyboard,
    m4_hero,
    m5_images,
    m6_animate,
    m7_voice,
    m8_assemble,
)

# модули в порядке прохождения (совпадает с jobs.MODULE_NAMES)
MODULES = [
    m1_idea,
    m2_script,
    m3_storyboard,
    m4_hero,
    m5_images,
    m6_animate,
    m7_voice,
    m8_assemble,
]


def run_pipeline(job: Job) -> None:
    """Запускается в фоновом потоке. Прогоняет задачу по конвейеру."""
    job.status = "running"
    workdir = Path(tempfile.mkdtemp(prefix=f"svet_{job.id}_"))
    job.context["workdir"] = workdir

    for i, module in enumerate(MODULES):
        state = job.modules[i]
        state.status = "running"
        state.started_at = time.time()
        try:
            detail = module.run(job, job.context)
            state.detail = detail or ""
            state.status = "done"
        except Exception as e:  # noqa: BLE001
            state.status = "error"
            state.detail = str(e)
            job.status = "error"
            job.error = f"{job.modules[i].name}: {e}"
            traceback.print_exc()
            return
        finally:
            state.finished_at = time.time()

    job.status = "done"
