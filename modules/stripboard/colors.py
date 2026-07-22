"""Color tokens for the Stripboard visual language."""

STRIP_COLORS = {
    "INT": "#60A5FA",
    "EXT": "#FACC15",
    "I/E": "#F472B6",
    "ESPECIAL": "#C084FC",
}

STRIP_SURFACES = {
    "panel": "#111827",
    "card": "#172033",
    "card_alt": "#1E293B",
    "border": "rgba(148, 163, 184, 0.18)",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
    "accent": "#F8B400",
}


def normalize_scene_type(value):
    """Map screenplay heading variants to a visual Stripboard category."""
    scene_type = str(value or "").strip().upper().replace(".", "")
    if scene_type in {"I/E", "INT/EXT", "INT-EXT", "INT EXT"}:
        return "I/E"
    if scene_type.startswith("INT"):
        return "INT"
    if scene_type.startswith("EXT"):
        return "EXT"
    return "ESPECIAL"


def get_strip_color(scene_type):
    return STRIP_COLORS[normalize_scene_type(scene_type)]
