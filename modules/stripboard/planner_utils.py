"""Read-only data adapters shared by the Stripboard presentation layer."""

from collections.abc import Iterable

from modules.stripboard.colors import normalize_scene_type


def scenes_to_records(scenes):
    """Return plain scene records without mutating the source dataframe."""
    if scenes is None:
        return []
    if hasattr(scenes, "empty") and scenes.empty:
        return []
    if hasattr(scenes, "to_dict"):
        return scenes.to_dict(orient="records")
    if isinstance(scenes, Iterable) and not isinstance(scenes, (str, bytes, dict)):
        return [dict(scene) for scene in scenes if isinstance(scene, dict)]
    return []


def paginate_records(records, page, page_size):
    """Return one bounded page and its display metadata."""
    total_records = len(records)
    total_pages = max(1, (total_records + page_size - 1) // page_size)
    current_page = max(1, min(int(page), total_pages))
    start_index = (current_page - 1) * page_size
    end_index = min(start_index + page_size, total_records)

    return {
        "records": records[start_index:end_index],
        "page": current_page,
        "total_pages": total_pages,
        "total_records": total_records,
        "start": start_index + 1 if total_records else 0,
        "end": end_index,
    }


def display_value(scene, *keys, default="—"):
    for key in keys:
        value = scene.get(key)
        if value is not None and str(value).strip():
            return value
    return default


def split_items(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    separator = "," if "," in text else ";"
    return [item.strip() for item in text.split(separator) if item.strip()]


def build_visible_summary(scenes):
    """Build the summary model for the currently visible read-only records."""
    records = scenes_to_records(scenes)
    unique_fields = {
        "Personajes": set(),
        "Locaciones": set(),
        "Looks": set(),
        "Props": set(),
        "Extras": set(),
        "Vehículos": set(),
        "Animales": set(),
        "VFX": set(),
        "Efectos Prácticos": set(),
        "Sonido": set(),
        "Notas": set(),
    }
    pages = set()
    eighths = []
    distribution = {"INT": 0, "EXT": 0, "I/E": 0, "ESPECIAL": 0}

    aliases = {
        "Locaciones": ("Locación", "Locacion"),
        "Efectos Prácticos": ("Efectos Prácticos", "SFX"),
    }

    for scene in records:
        page = display_value(scene, "Página", "Pagina", default="")
        if str(page).strip():
            pages.add(str(page).strip())
        eighth = display_value(scene, "Octavos", default="")
        if str(eighth).strip():
            eighths.append(str(eighth).strip())
        distribution[normalize_scene_type(scene.get("INT/EXT"))] += 1

        for label in unique_fields:
            keys = aliases.get(label, (label,))
            value = display_value(scene, *keys, default="")
            unique_fields[label].update(split_items(value))

    return {
        "Escenas": len(records),
        "Páginas": len(pages),
        "Octavos": len(eighths),
        **{label: len(values) for label, values in unique_fields.items()},
        "Distribución": distribution,
    }
