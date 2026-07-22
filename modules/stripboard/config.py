"""Configuration for the read-only Stripboard V1 interface."""

DEFAULT_PANEL_WIDTHS = (1.05, 3.8, 1.15)
PLANNING_PANEL_WIDTHS = (1.05, 3.8, 1.15)

WORKSPACE_PANEL_HEIGHT = 760
STRIP_LIST_HEIGHT = 500
PAGE_SIZE_OPTIONS = (10, 25, 50, 100)
DEFAULT_PAGE_SIZE = PAGE_SIZE_OPTIONS[0]

DEFAULT_STRIP_HEIGHT = 82
VIEW_MODES = {
    "compact": {"label": "Compacta", "strip_height": 62},
    "expanded": {"label": "Expandida", "strip_height": DEFAULT_STRIP_HEIGHT},
}

STRIP_COLUMNS = (
    "Color",
    "Escena",
    "INT/EXT",
    "Encabezado",
    "Locación",
    "Día/Noche",
    "Página",
    "Octavos",
    "Personajes",
    "Extras",
    "Props",
    "VFX",
    "Estado",
    "Notas",
)

DEFAULT_VISIBLE_COLUMNS = (
    "Escena",
    "INT/EXT",
    "Encabezado",
    "Locación",
    "Día/Noche",
    "Página",
    "Octavos",
    "Personajes",
    "Extras",
    "Props",
    "VFX",
    "Estado",
    "Notas",
)

VISIBLE_INFORMATION_OPTIONS = (
    "Página",
    "Escenas por página",
    "Octavos",
    "Personajes",
    "Actores",
    "Looks",
    "Props",
    "Vestuario",
    "Maquillaje",
    "Extras",
    "Vehículos",
    "Animales",
    "VFX",
    "Sonido",
    "Notas",
    "Producción",
    "Estado",
    "Continuidad",
)

SAVED_VIEWS = ()

FUTURE_FEATURES = (
    "drag_and_drop",
    "saved_views",
    "visible_columns",
    "compact_view",
    "expanded_view",
    "scene_detail_panel",
    "planning_data",
    "shooting_schedule_sync",
)
