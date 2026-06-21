"""Pollinations.ai — бесплатная генерация картинок БЕЗ ключей и регистрации.

Картинку отдаёт прямо по URL: image.pollinations.ai/prompt/<текст>?width=&height=.
Рисует у себя (не грузит наш слабый сервер). Возвращает bytes или None.

Это основной «художник» проекта: OpenClaw под подпиской ChatGPT картинки НЕ умеет
(только текст), поэтому изображения берём здесь — и всё остаётся бесплатным.
"""
import urllib.parse

import requests

from .. import config

TIMEOUT = 75


def _log(msg: str) -> None:
    print(f"[pollinations] {msg}", flush=True)


def generate_image(prompt: str, width: int = 768, height: int = 1344,
                   seed: int | None = None, image_url: str | None = None,
                   model: str | None = None) -> bytes | None:
    """Текст -> картинка (PNG/JPEG bytes). None при ошибке -> сработает запасной путь.

    Если задан image_url — режим «по картинке-образцу» (image-to-image): художнику
    показываем эталон героя, и он рисует ТО ЖЕ лицо в новой сцене. Для этого нужна
    модель, умеющая принимать образец (model='kontext'), иначе образец игнорируется.
    """
    if not config.USE_POLLINATIONS:
        return None
    q = urllib.parse.quote((prompt or "")[:1500])
    params = {"width": width, "height": height, "nologo": "true",
              "model": model or config.POLLINATIONS_MODEL}
    if seed is not None:
        params["seed"] = seed
    if image_url:
        params["image"] = image_url   # эталон героя -> консистентность лица
    url = f"https://image.pollinations.ai/prompt/{q}"
    for attempt in range(2):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT)
            sig = r.content[:4]
            if r.status_code == 200 and (sig == b"\x89PNG" or sig[:3] == b"\xff\xd8\xff"):
                return r.content
            _log(f"попытка {attempt+1}: код {r.status_code}, не картинка ({r.content[:80]!r})")
        except Exception as e:  # noqa: BLE001
            _log(f"попытка {attempt+1}: ошибка {e}")
    return None
