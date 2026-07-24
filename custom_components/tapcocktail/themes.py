from __future__ import annotations

COCKTAIL_THEMES = {
    "klassisk": {"label": "🍹 Klassisk cocktail", "icon": "🍹", "color": "#FF8C00"},
    "martini": {"label": "🍸 Martini / elegant", "icon": "🍸", "color": "#C0C0C0"},
    "citrus": {"label": "🍊 Citrus", "icon": "🍊", "color": "#FFA500"},
    "lemonade": {"label": "🍋 Lemonade", "icon": "🍋", "color": "#FFF176"},
    "tropisk": {"label": "🌺 Tropisk", "icon": "🌺", "color": "#FF6F61"},
    "mango": {"label": "🥭 Mango", "icon": "🥭", "color": "#FFC107"},
    "baer": {"label": "🍓 Bær", "icon": "🍓", "color": "#E91E63"},
    "kirsebaer": {"label": "🍒 Kirsebær", "icon": "🍒", "color": "#D32F2F"},
    "aeble": {"label": "🍏 Æble", "icon": "🍏", "color": "#8BC34A"},
    "frisk_urter": {"label": "🌿 Frisk / urter", "icon": "🌿", "color": "#4CAF50"},
    "cremet": {"label": "🥥 Cremet", "icon": "🥥", "color": "#FFF3E0"},
    "dessert": {"label": "☕ Dessert", "icon": "☕", "color": "#795548"},
    "fad_oel": {"label": "🍺 Fad / øl-look", "icon": "🍺", "color": "#D4A017"},
    "frozen": {"label": "🧊 Frozen", "icon": "🧊", "color": "#81D4FA"},
    "eksotisk": {"label": "🌴 Eksotisk", "icon": "🌴", "color": "#00BCD4"},
    "vinbaseret": {"label": "🍷 Vinbaseret", "icon": "🍷", "color": "#8E24AA"},
    "spritz": {"label": "🥂 Spritz", "icon": "🥂", "color": "#FF7043"},
    "mocktail": {"label": "🥤 Mocktail", "icon": "🥤", "color": "#26A69A"},
    "vand_sodavand": {"label": "💧 Vand / sodavand", "icon": "💧", "color": "#29B6F6"},
}

def get_theme(theme_id):
    return COCKTAIL_THEMES.get(theme_id or "", COCKTAIL_THEMES["klassisk"])
