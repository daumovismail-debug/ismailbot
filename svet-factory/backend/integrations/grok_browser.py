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

from .. import config

try:
    from playwright.sync_api import sync_playwright
    _HAS_PW = True
except Exception:  # noqa: BLE001
    _HAS_PW = False


def _log(msg: str) -> None:
    print(f"[grok-browser] {msg}", flush=True)


def available() -> bool:
    if not config.USE_GROK_BROWSER:
        return False
    if not _HAS_PW:
        _log("playwright не установлен (pip install playwright + playwright install chromium)")
        return False
    if not Path(config.GROK_STATE_FILE).exists():
        _log(f"нет файла сессии grok.com: {config.GROK_STATE_FILE} (экспортируй cookies)")
        return False
    return True


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
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            ctx = browser.new_context(storage_state=config.GROK_STATE_FILE)
            page = ctx.new_page()
            page.set_default_timeout(60_000)
            page.goto(config.GROK_URL, wait_until="domcontentloaded")

            # 1) загрузить кадр (image-to-video). Ищем file input.
            page.set_input_files("input[type=file]", image_path)

            # 2) вписать промпт движения
            box = page.locator(config.GROK_SEL_PROMPT).first
            box.fill(prompt)

            # 3) запустить генерацию
            page.locator(config.GROK_SEL_SUBMIT).first.click()

            # 4) дождаться готового видео и забрать его src
            video = page.locator("video").first
            video.wait_for(state="visible", timeout=config.GROK_WAIT_MS)
            src = video.get_attribute("src")
            data = None
            if src:
                # скачиваем mp4 в контексте сессии (если blob: — берём через fetch)
                if src.startswith("http"):
                    resp = ctx.request.get(src)
                    if resp.ok:
                        data = resp.body()
                else:
                    data = page.evaluate(
                        """async (s) => { const r = await fetch(s);
                           const b = await r.arrayBuffer();
                           return Array.from(new Uint8Array(b)); }""", src)
                    data = bytes(data) if data else None
            ctx.close()
            browser.close()
            if data:
                _log("видео получено через подписку ✅")
                return data
            _log("видео не нашлось на странице (см. селекторы)")
            return None
    except Exception as e:  # noqa: BLE001
        _log(f"ошибка автоматизации: {e}")
        try:
            if page:
                page.screenshot(path=str(shot))   # скриншот для отладки селекторов
                _log(f"скриншот сохранён: {shot}")
        except Exception:  # noqa: BLE001
            pass
        return None
