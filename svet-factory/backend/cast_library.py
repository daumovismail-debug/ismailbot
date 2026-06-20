"""Библиотека персонажей сериала (каста) + детектор по сценарию.

Героиня — постоянный бренд-герой (всегда в касте). Второстепенных находим в
репликах/действиях по ключевым словам (RU+KZ) и берём их паспорт-заготовку из
casting.md. Пользователь потом может поправить/добавить или принять авто-вариант.
"""

# Паспорта-заготовки (из casting.md). auto=True — предложено системой.
HEROINE = {
    "id": "heroine", "name": "Героиня", "type": "human", "gender": "female", "age": 31,
    "face": "мягкое сердцевидное лицо, большие карие глаза, без волос — "
            "вместо них хрустальная люстра-корона (тёплое золото), светится по эмоции",
    "skin": "светло-смуглая", "outfit": "кремово-золотое платье",
    "signature": "корона-люстра, свет = эмоция", "character": "добрая, ранимая, сильная",
    "voice_hint": "тёплый искренний женский", "voice_id": "VOICE_HEROINE", "auto": False,
}

LIBRARY = {
    "husband": {
        "id": "husband", "name": "Муж", "type": "human", "gender": "male", "age": 32,
        "face": "тёмные короткие волосы, лёгкая щетина, прямые брови",
        "skin": "светлая", "outfit": "синяя рубашка, тёмные джинсы",
        "signature": "часто хмурится", "character": "скуповат, упрям, в душе любит",
        "voice_hint": "низкий уверенный мужской", "voice_id": "VOICE_HUSBAND", "auto": True,
    },
    "mother_in_law": {
        "id": "mother_in_law", "name": "Свекровь", "type": "human", "gender": "female", "age": 55,
        "face": "седой пучок, строгий взгляд, поджатые губы",
        "skin": "светлая", "outfit": "тёмное закрытое платье",
        "signature": "властная осанка", "character": "властная, колкая",
        "voice_hint": "резкий повелительный женский", "voice_id": "VOICE_MIL", "auto": True,
    },
    "neighbor": {
        "id": "neighbor", "name": "Соседка", "type": "human", "gender": "female", "age": 33,
        "face": "крашеный блонд, яркий макияж",
        "skin": "светлая", "outfit": "модный костюм",
        "signature": "фальшивая улыбка", "character": "завистливая",
        "voice_hint": "сладкий, но фальшивый женский", "voice_id": "VOICE_NEIGHBOR", "auto": True,
    },
    "cat": {
        "id": "cat", "name": "Кот-Люстра", "type": "cat", "gender": "male", "age": 3,
        "face": "пушистый кот с маленькой хрустальной люстрой-короной",
        "skin": "рыже-кремовая шерсть", "outfit": "—",
        "signature": "люстра-корона, как у героини", "character": "забавный, хитрый",
        "voice_hint": "мультяшный, без слов (мяу/реакции)", "voice_id": "VOICE_CAT", "auto": True,
    },
}

# ключевые слова (RU + разговорный KZ) → id персонажа
_KEYS = {
    "husband": ["муж", "мужу", "мужа", "супруг", "күйеу", "ері", "еркек"],
    "mother_in_law": ["свекров", "свекр", "ене", "енесі", "қайнене"],
    "neighbor": ["соседк", "сосед", "көрші"],
    "cat": ["кот", "кошк", "кошек", "мысық", "котик"],
}


def detect(scenes: list) -> list[dict]:
    """Героиня + второстепенные, найденные в сценарии. Возвращает список паспортов."""
    blob = " ".join(
        f"{s.get('voice','')} {s.get('voice_ru','')} {s.get('beat','')}".lower()
        for s in scenes
    )
    cast = [dict(HEROINE)]
    for cid, words in _KEYS.items():
        if any(w in blob for w in words):
            cast.append(dict(LIBRARY[cid]))
    return cast


def passport_prompt(p: dict, hero_passport: str) -> str:
    """Промпт-эталон персонажа из его паспорта (героиня — канон, остальные — по полям)."""
    if p.get("id") == "heroine":
        return hero_passport
    kind = "cat" if p.get("type") == "cat" else "character"
    return (
        f"Pixar/Disney 3D animated {kind} reference, single character, "
        f"{p.get('gender','')}, age {p.get('age','')}, {p.get('face','')}, "
        f"skin/fur {p.get('skin','')}, wearing {p.get('outfit','')}, "
        f"{p.get('signature','')}. Plain light-grey background, flat even lighting, "
        f"vertical 9:16. Series palette: warm gold, cream-beige, deep burgundy. "
        f"Unreal Engine 5 render, soft subsurface shading."
    )
