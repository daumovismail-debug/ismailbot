"""Оркестратор: гоняет 8 модулей строго по очереди, обновляя статусы задачи."""
import time
import traceback

from . import config
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
    # рабочая папка внутри output/, чтобы кадры были доступны по публичному URL
    workdir = config.OUTPUT_DIR / job.id
    workdir.mkdir(parents=True, exist_ok=True)
    job.context["workdir"] = workdir
    if config.PUBLIC_BASE_URL:
        job.context["media_base"] = f"{config.PUBLIC_BASE_URL}/media/{job.id}"

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
