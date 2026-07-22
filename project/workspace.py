"""Framework-independent CinePlan Workspace context model."""

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime

from project.project_metadata import CINEPLAN_VERSION, utc_now


WORKSPACE_VERSION = 2
MAX_HISTORY = 10
MODULE_KEYS = {
    "Proyecto": "dashboard",
    "Importar y revisar": "1. Importar y analizar guion",
    "Breakdown": "2. Breakdown",
    "Stripboard": "3. Stripboard",
    "Rodaje": "4. Rodaje",
    "Llamados": "5. Llamados",
    "Exportar": "6. Exportar",
}


def empty_workspace_context():
    return {
        "project": "",
        "module": "Proyecto",
        "submodule": "Dashboard",
        "scene": {"id": "", "number": "", "heading": ""},
        "character": "",
        "location": "",
        "day": "",
        "strip": "",
        "document": "",
        "filters": {},
        "saved_view": "",
        "sidebar": "default",
        "theme": "CinePlan oscuro",
        "zoom": "",
        "window_layout": "default",
        "timestamp": "",
        "session_started_at": utc_now(),
        "last_saved_at": "",
        "last_modified_at": "",
        "session_duration_seconds": None,
        "last_action": "",
        "history": [],
        "automatic_restore": False,
        "cineplan_version": CINEPLAN_VERSION,
        "workspace_version": WORKSPACE_VERSION,
    }


class WorkspaceContext:
    """Explicit user context with no dependency on Streamlit or widget state."""

    def __init__(self, data=None):
        self._data = empty_workspace_context()
        if isinstance(data, Mapping):
            # One-time compatibility with the first Workspace prototype.
            legacy_scene = {
                "id": data.get("last_scene_id", ""),
                "number": data.get("last_scene_number", ""),
                "heading": data.get("last_scene_heading", ""),
            }
            legacy = {
                "module": data.get("last_module"),
                "submodule": data.get("last_submodule"),
                "scene": legacy_scene if any(legacy_scene.values()) else None,
                "character": data.get("selected_character"),
                "location": data.get("selected_location"),
                "day": data.get("last_day"),
                "strip": data.get("last_strip"),
                "document": data.get("selected_document"),
                "filters": data.get("active_filters"),
                "timestamp": data.get("last_saved_timestamp"),
                "automatic_restore": data.get("restore_automatically"),
            }
            for key, value in legacy.items():
                if key not in data and value is not None:
                    self._data[key] = deepcopy(value)
            for key in self._data:
                if key in data:
                    self._data[key] = deepcopy(data[key])
        if not isinstance(self._data.get("scene"), Mapping):
            self._data["scene"] = {"id": "", "number": "", "heading": ""}
        if not isinstance(self._data.get("filters"), Mapping):
            self._data["filters"] = {}
        if not isinstance(self._data.get("history"), list):
            self._data["history"] = []

    def begin_module(self, module):
        self._data["module"] = str(module or "Proyecto")

    def begin_submodule(self, submodule):
        self._data["submodule"] = str(submodule or "")

    def set_scene(self, scene_id="", number="", heading=""):
        self._data["scene"] = {
            "id": str(scene_id or number or ""),
            "number": str(number or ""),
            "heading": str(heading or ""),
        }

    def set_character(self, value): self._data["character"] = str(value or "")
    def set_location(self, value): self._data["location"] = str(value or "")
    def set_day(self, value): self._data["day"] = str(value or "")
    def set_strip(self, value): self._data["strip"] = str(value or "")
    def set_document(self, value): self._data["document"] = str(value or "")
    def set_saved_view(self, value): self._data["saved_view"] = str(value or "")
    def set_sidebar(self, value): self._data["sidebar"] = str(value or "default")
    def set_theme(self, value): self._data["theme"] = str(value or "")
    def set_zoom(self, value): self._data["zoom"] = str(value or "")
    def set_window_layout(self, value): self._data["window_layout"] = str(value or "")

    def set_filter(self, name, value):
        if name:
            self._data["filters"][str(name)] = deepcopy(value)

    def set_automatic_restore(self, enabled):
        self._data["automatic_restore"] = bool(enabled)

    def merge_provider_values(self, values):
        """Merge clean CinePlan concepts returned by registered providers."""
        if not isinstance(values, Mapping):
            return
        for key in (
            "module", "submodule", "character", "location", "day", "strip",
            "document", "saved_view", "sidebar", "theme", "zoom", "window_layout",
        ):
            if key in values and values[key] is not None:
                self._data[key] = deepcopy(values[key])
        if isinstance(values.get("scene"), Mapping):
            scene = values["scene"]
            self.set_scene(scene.get("id"), scene.get("number"), scene.get("heading"))
        if isinstance(values.get("filters"), Mapping):
            self._data["filters"].update(deepcopy(values["filters"]))

    def record_event(self, action, timestamp=None):
        timestamp = timestamp or utc_now()
        self._data["timestamp"] = timestamp
        self._data["last_modified_at"] = timestamp
        self._data["last_action"] = str(action or "Contexto actualizado")
        scene = self._data.get("scene", {})
        entry = {
            "timestamp": timestamp,
            "module": self._data.get("module", ""),
            "submodule": self._data.get("submodule", ""),
            "scene": scene.get("number", ""),
            "character": self._data.get("character", ""),
            "location": self._data.get("location", ""),
            "day": self._data.get("day", ""),
            "strip": self._data.get("strip", ""),
            "document": self._data.get("document", ""),
            "action": self._data["last_action"],
        }
        self._data["history"] = [entry, *self._data.get("history", [])][:MAX_HISTORY]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def to_dict(self):
        return deepcopy(self._data)


def migrate_workspace_context(context):
    """Normalize legacy workspace/workspace_context schemas to the current version."""
    migrated = WorkspaceContext(context).to_dict()
    migrated["workspace_version"] = WORKSPACE_VERSION
    return migrated


def build_workspace_context(context, last_saved_timestamp=None, project_name=""):
    """Serialize an already-live context; no navigation is discovered here."""
    workspace = migrate_workspace_context(context)
    timestamp = last_saved_timestamp or utc_now()
    workspace["project"] = str(project_name or workspace.get("project") or "")
    workspace["timestamp"] = timestamp
    workspace["last_saved_at"] = timestamp
    workspace["cineplan_version"] = CINEPLAN_VERSION
    workspace["workspace_version"] = WORKSPACE_VERSION
    started = workspace.get("session_started_at")
    try:
        start_time = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        workspace["session_duration_seconds"] = max(0, int((end_time - start_time).total_seconds()))
    except (TypeError, ValueError):
        workspace["session_duration_seconds"] = None
    return workspace


def restore_workspace_context(
    context, available_modules=None, available_scenes=None,
    available_characters=None, available_strips=None,
):
    """Return a navigation plan containing CinePlan concepts only."""
    workspace = migrate_workspace_context(context)
    modules = set(available_modules or MODULE_KEYS)
    module = workspace.get("module")
    if module not in modules or module not in MODULE_KEYS:
        return {"view": "dashboard", "module_key": "", "context": workspace}
    scene = workspace.get("scene", {})
    if available_scenes is not None and str(scene.get("number", "")) not in {
        str(number) for number in available_scenes
    }:
        workspace["scene"] = {"id": "", "number": "", "heading": ""}
    if available_characters is not None and workspace.get("character") not in {
        str(value) for value in available_characters
    }:
        workspace["character"] = ""
    if available_strips is not None and str(workspace.get("strip", "")) not in {
        str(value) for value in available_strips
    }:
        workspace["strip"] = ""
    return {
        "view": "dashboard" if module == "Proyecto" else "modules",
        "module_key": MODULE_KEYS[module],
        "context": workspace,
    }


def format_saved_datetime(value):
    try:
        saved = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        months = (
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        )
        return f"{saved.day:02d} {months[saved.month - 1]} {saved.year}", saved.strftime("%H:%M")
    except (TypeError, ValueError):
        return "—", "—"
