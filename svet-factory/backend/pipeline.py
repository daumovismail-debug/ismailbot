"""Оркестратор: гоняет 8 модулей строго по очереди, обновляя статусы задачи."""
import time
import traceback

from . import config
from .jobs import Job, store
from .validate import validate
from .modules import (
    m1_idea,
    m2_script,
    m_cast,
    m3_storyboard,
    m4_hero,
    m5_images,
    m6_animate,
    m7_voice,
    m8_assemble,
    m9_control,
    m12_review,
    m11_analyst,
    m10_publish,
)

# модули в порядке прохождения (совпадает с jobs.MODULE_NAMES)
MODULES = [
    m1_idea,
    m2_script,
    m_cast,
    m3_storyboard,
    m4_hero,
    m5_images,
    m6_animate,
    m7_voice,
    m8_assemble,
    m9_control,
    m12_review,
    m11_analyst,
    m10_publish,
]

# порядок и число модулей должны строго совпадать с jobs.MODULE_NAMES,
# иначе job.modules[i] и MODULES[i] разъедутся
from .jobs import MODULE_NAMES  # noqa: E402
assert len(MODULES) == len(MODULE_NAMES), "MODULES != MODULE_NAMES"


def run_pipeline(job: Job, start: int = 0) -> None:
    """Запускается в фоновом потоке. Прогоняет задачу по конвейеру с `start`-модуля.

    Если модуль помечен PAUSE_AFTER (кастинг) — останавливаемся со статусом
    awaiting_cast и запоминаем, с какого модуля продолжить (job.pause_index).
    """
    job.status = "running"
    # рабочая папка внутри output/, чтобы кадры были доступны по публичному URL
    workdir = config.OUTPUT_DIR / job.id
    workdir.mkdir(parents=True, exist_ok=True)
    job.context["workdir"] = workdir
    if config.PUBLIC_BASE_URL:
        job.context["media_base"] = f"{config.PUBLIC_BASE_URL}/media/{job.id}"
    store.save(job)

    for i in range(start, len(MODULES)):
        module = MODULES[i]
        state = job.modules[i]
        state.status = "running"
        state.started_at = time.time()
        # живой прогресс внутри модуля (например "рисую кадр 2/5…")
        job.context["_progress"] = (
            lambda text, s=state, j=job: (setattr(s, "detail", text), store.save(j))
        )
        store.save(job)
        try:
            detail = module.run(job, job.context)
            state.detail = detail or ""
            state.status = "done"
            # гейт-проверка контракта (SCHEMA): не валим, но помечаем
            warns = validate(state.name, job.context)
            if warns:
                state.detail = (state.detail + "  ⚠ гейт: " + "; ".join(warns)).strip()
        except Exception as e:  # noqa: BLE001
            state.status = "error"
            state.detail = str(e)
            job.status = "error"
            job.error = f"{job.modules[i].name}: {e}"
            traceback.print_exc()
            state.finished_at = time.time()
            store.save(job)
            return
        finally:
            state.finished_at = time.time()
            store.save(job)

        # пауза для подтверждения касты (только если не подтверждена ранее)
        if getattr(module, "PAUSE_AFTER", False) and not job.context.get("cast_confirmed"):
            job.pause_index = i + 1
            job.status = "awaiting_cast"
            store.save(job)
            return

    job.status = "done"
    store.save(job)
