"""Grok Imagine через ПОДПИСКУ (без API-ключа) — автоматизация браузера grok.com.

Запускает невидимый Chromium с твоей сохранённой сессией grok.com (cookies),
загружает кадр, просит сделать видео (image-to-video) и скачивает готовый mp4.
Это использует ТВОЮ подписку Grok, без оплаты за API.

⚠️ ВАЖНО (прочитай перед включением):
- ТЯЖЁЛОЕ: Chromium ест 300–700 МБ → нужен сервер ≥2 ГБ (на 1 ГБ упадёт).
- НУЖНА СЕССИЯ: экспортируй cookies/состояние grok.com в файл GROK_STATE_FILE
  (один раз; иначе grok.com попросит логин). Как — см. README.
- ХРУПКОЕ: grok.com меняет вёрстку → селекторы (GROK_SEL_*) могут потребовать
  правки. При сбое сохраняем скриншот рядом с кадром — по нему чиним.
- Выключено по умолчанию (USE_GROK_BROWSER=0). Сбой = тихо None → Ken Burns.

Установка на сервере:
    pip3 install playwright --break-system-packages
    python3 -m playwright install chromium
"""
from pathlib import Path

import time

from .. import config

try:
    from playwright.sync_api import sync_playwright
    _HAS_PW = True
except Exception:  # noqa: BLE001
    _HAS_PW = False


def _log(msg: str) -> None:
    print(f"[grok-browser] {msg}", flush=True)


# Экономные флаги Chromium — чтобы влезть в маленькую память (1 ГБ + swap).
LAUNCH_ARGS = [
    "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
    "--disable-extensions", "--disable-background-networking",
    "--disable-renderer-backgrounding", "--disable-background-timer-throttling",
    "--no-first-run", "--no-zygote", "--mute-audio",
    "--js-flags=--max-old-space-size=256",
]


def available() -> bool:
    # включён хотя бы один режим Grok-браузера (видео или картинки)
    if not (config.USE_GROK_BROWSER or config.USE_GROK_IMAGES):
        return False
    if not _HAS_PW:
        _log("playwright не установлен (pip install playwright + playwright install chromium)")
        return False
    if not Path(config.GROK_STATE_FILE).exists():
        _log(f"нет файла сессии grok.com: {config.GROK_STATE_FILE} (экспортируй cookies)")
        return False
    return True


def _dismiss_overlays(page) -> None:
    """Закрывает баннер cookies (OneTrust) и модалку «что нового» — они
    перекрывают поле ввода и перехватывают клики."""
    # 1) cookies (OneTrust) — у кнопок согласия фиксированные id
    for sel in ("#onetrust-accept-btn-handler", "#onetrust-reject-all-handler",
                'button:has-text("Accept All Cookies")', 'button:has-text("Reject All")'):
        try:
            page.locator(sel).first.click(timeout=2500)
            break
        except Exception:  # noqa: BLE001
            continue
    page.wait_for_timeout(400)
    # 2) модалка «что нового» — кнопка Get Started или крестик
    for sel in ('button:has-text("Get Started")', 'button:has-text("Get started")',
                '[aria-label="Close"]', 'button:has-text("Close")'):
        try:
            page.locator(sel).first.click(timeout=2500)
            break
        except Exception:  # noqa: BLE001
            continue
    try:
        page.keyboard.press("Escape")
    except Exception:  # noqa: BLE001
        pass
    page.wait_for_timeout(800)


def _type_prompt(page, prompt: str) -> bool:
    """Печатает запрос в поле ввода grok.com. Это contenteditable-редактор
    (tiptap/ProseMirror), а НЕ textarea — поэтому кликаем и печатаем с клавиатуры."""
    selectors = [config.GROK_SEL_PROMPT, ".tiptap.ProseMirror",
                 "div[contenteditable='true']", "textarea"]
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            loc.wait_for(state="visible", timeout=8000)
        except Exception:  # noqa: BLE001
            continue
        loc.click()
        page.keyboard.type(prompt, delay=5)
        return True
    return False


def generate_video(image_path: str, prompt: str, seconds: int = 6,
                   debug_dir: str | None = None) -> bytes | None:
    """Оживляет кадр через grok.com Imagine под твоей подпиской. -> mp4 bytes или None."""
    if not available():
        return None
    shot = Path(debug_dir or Path(image_path).parent) / "grok_debug.png"
    page = None
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=LAUNCH_ARGS,
            )
            ctx = browser.new_context(storage_state=config.GROK_STATE_FILE)
            page = ctx.new_page()
            page.set_default_timeout(60_000)
            page.goto(config.GROK_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            _dismiss_overlays(page)   # закрыть cookies-баннер и модалку

            # 0) переключиться в режим ВИДЕО (вкладка Video у поля ввода)
            for sel in ('button:has-text("Video")', '[role=tab]:has-text("Video")',
                        'text="Video"'):
                try:
                    page.locator(sel).first.click(timeout=4000)
                    break
                except Exception:  # noqa: BLE001
                    continue
            page.wait_for_timeout(1500)

            # видео, что УЖЕ есть на странице (история) — чтобы потом отличить НОВОЕ
            def _vsrc():
                return page.eval_on_selector_all(
                    "video",
                    "els => els.map(e => e.currentSrc || e.src || "
                    "(e.querySelector('source') ? e.querySelector('source').src : ''))")
            before = set(s for s in _vsrc() if s)

            # 1) загрузить НАШ кадр (image-to-video)
            try:
                page.set_input_files("input[type=file]", image_path)
                page.wait_for_timeout(2000)
            except Exception:  # noqa: BLE001
                pass

            # 2) вписать промпт движения и 3) запустить (Enter)
            if _type_prompt(page, prompt):
                page.keyboard.press("Enter")

            # 4) дождаться НОВОГО готового видео (не из истории) и скачать его
            deadline = time.monotonic() + config.GROK_WAIT_MS / 1000
            data = None
            while time.monotonic() < deadline and not data:
                new = [s for s in _vsrc() if s and s not in before]
                for src in new:
                    d = _download_src(ctx, page, src)
                    if d and len(d) > 500_000:    # реальный клип (МБ), не превью
                        data = d
                        break
                if not data:
                    page.wait_for_timeout(5000)

            if not data and page:
                page.screenshot(path=str(shot))
                _log(f"новое видео не нашлось — скриншот: {shot}")
            ctx.close()
            browser.close()
            if data:
                _log("видео получено через подписку ✅")
            return data
    except Exception as e:  # noqa: BLE001
        _log(f"ошибка автоматизации: {e}")
        try:
            if page:
                page.screenshot(path=str(shot))   # скриншот для отладки селекторов
                _log(f"скриншот сохранён: {shot}")
        except Exception:  # noqa: BLE001
            pass
        return None


def _is_image(d: bytes | None) -> bool:
    """PNG/JPEG достаточного размера (отсекаем иконки-обрезки интерфейса)."""
    return bool(d) and len(d) > 8000 and (d[:4] == b"\x89PNG" or d[:3] == b"\xff\xd8\xff")


def _looks_generated(src: str) -> bool:
    """Похоже ли это на СГЕНЕРИРОВАННУЮ картинку, а не на иконку интерфейса."""
    if not src:
        return False
    if src.startswith(("blob:", "data:")):
        return True
    s = src.lower()
    if any(x in s for x in ("logo", "icon", "avatar", "favicon", "sprite", ".svg")):
        return False
    return s.startswith("http")


def _download_src(ctx, page, src: str) -> bytes | None:
    """Скачиваем медиа по src (http / blob / data) в контексте сессии."""
    try:
        if src.startswith("http"):
            resp = ctx.request.get(src)
            return resp.body() if resp.ok else None
        if src.startswith(("blob:", "data:")):
            arr = page.evaluate(
                """async (s) => { const r = await fetch(s);
                   const b = await r.arrayBuffer();
                   return Array.from(new Uint8Array(b)); }""", src)
            return bytes(arr) if arr else None
    except Exception:  # noqa: BLE001
        return None
    return None


def generate_image(prompt: str, debug_dir: str | None = None) -> bytes | None:
    """Рисует КАРТИНКУ через grok.com Imagine под твоей подпиской. -> bytes или None.

    Используется для эталона героя (Модуль 4) и кадров раскадровки (Модуль 5).
    """
    if not available():
        return None
    shot = Path(debug_dir or ".") / "grok_img_debug.png"
    page = None
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=LAUNCH_ARGS,
            )
            ctx = browser.new_context(storage_state=config.GROK_STATE_FILE)
            page = ctx.new_page()
            page.set_default_timeout(60_000)
            page.goto(config.GROK_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            _dismiss_overlays(page)   # закрыть cookies-баннер и модалку

            typed = _type_prompt(page, prompt)
            if typed:
                page.keyboard.press("Enter")

            # Резкая версия у Grok появляется НЕ сразу (~1.5–2 мин): сначала мягкое
            # превью ~100КБ, потом чёткие ~200–260КБ. Поэтому ждём и берём САМУЮ
            # ТЯЖЁЛУЮ из сгенерированных картинок — она и есть финальная резкая.
            best, best_size = None, 0
            if typed:
                page.wait_for_timeout(70_000)   # дать генерации стартовать
                deadline = time.monotonic() + max(30, config.GROK_IMG_WAIT_MS / 1000)
                while time.monotonic() < deadline:
                    srcs = page.eval_on_selector_all(
                        "img", "els => els.filter(e => e.naturalWidth >= 400).map(e => e.src)")
                    for s in srcs:
                        if not _looks_generated(s):
                            continue
                        d = _download_src(ctx, page, s)
                        if _is_image(d) and len(d) > best_size:
                            best, best_size = d, len(d)
                    if best_size >= 180_000:    # уверенно финальная резкая картинка
                        break
                    page.wait_for_timeout(10_000)
            data = best   # самая тяжёлая = самая чёткая (если нашли)

            if not data and page:
                page.screenshot(path=str(shot))   # для тюнинга селекторов
                _log(f"картинка не найдена — скриншот: {shot}")
            ctx.close()
            browser.close()
            if data:
                _log("картинка получена через подписку ✅")
            return data
    except Exception as e:  # noqa: BLE001
        _log(f"ошибка генерации картинки: {e}")
        try:
            if page:
                page.screenshot(path=str(shot))
                _log(f"скриншот сохранён: {shot}")
        except Exception:  # noqa: BLE001
            pass
        return None
