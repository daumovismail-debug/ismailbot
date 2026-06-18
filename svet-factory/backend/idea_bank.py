"""Банк тем-драм для ниши «люстры / свет», аудитория — женщины 30+.

Каждая тема построена на приёме: СВЕТ героини = её ЭМОЦИИ.
"""

HERO_PASSPORT = (
    "Pixar-style 3D animated character, a beautiful elegant woman in her 30s, "
    "warm friendly face, soft features, gentle expressive eyes. Instead of hair "
    "she wears an elegant glowing crystal chandelier as a crown, warm golden "
    "light, delicate crystals. Cozy cinematic lighting, Pixar Disney render "
    "style, soft skin shading. Vertical 9:16."
)

IDEA_BANK = [
    {
        "theme": "Та, что светила всем",
        "message": "Женщина годами светит для всех, кроме себя — и однажды "
                   "решает зажечь свой свет ради себя.",
    },
    {
        "theme": "Муж сказал «дорого»",
        "message": "Муж не оценил её желание света и красоты — а потом сам "
                   "понял, как с ней засиял весь дом.",
    },
    {
        "theme": "Свекровь назвала мещанством",
        "message": "Героиню осудили за любовь к красивому свету — но именно её "
                   "тепло согрело всю семью.",
    },
    {
        "theme": "Дорогой ремонт, дешёвый свет",
        "message": "Всё в доме идеально, но тусклый холодный свет всё убивает — "
                   "пока героиня не меняет свет и не оживает сама.",
    },
    {
        "theme": "Погасла ради других",
        "message": "Героиня почти погасла, отдавая тепло всем вокруг — и нашла "
                   "силы загореться снова.",
    },
]


def pick(theme: str | None) -> dict:
    """Берём тему из банка по названию или первую попавшуюся."""
    if theme:
        for item in IDEA_BANK:
            if item["theme"].lower() == theme.strip().lower():
                return item
        # пользовательская тема, которой нет в банке
        return {"theme": theme.strip(), "message": theme.strip()}
    return IDEA_BANK[0]
