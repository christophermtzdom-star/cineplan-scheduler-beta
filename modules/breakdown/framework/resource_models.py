"""Framework-neutral models for project-owned Breakdown resources."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class InspectorField:
    key: str
    label: str
    kind: str = "text"
    options: tuple[str, ...] = ()
    section: str = "General"
    scope: str = "assignment"
    read_only: bool = False


@dataclass(frozen=True)
class ResourceModuleConfig:
    resource_type: str
    id_prefix: str
    label: str
    categories: tuple[str, ...]
    statuses: tuple[str, ...]
    inspector_fields: tuple[InspectorField, ...] = ()
    legacy_categories: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    allow_duplicate_creation: bool = True
    material_symbol: str = ""


def empty_store():
    return {
        "schema_version": 1,
        "resources": {},
        "assignments": {},
        "sequences": {},
        "events": [],
    }


def new_resource(resource_id, resource_type, name, category, **values):
    now = utc_now()
    record = {
        "id": resource_id,
        "resource_type": resource_type,
        "name": str(name or "").strip(),
        "category": str(category or "").strip(),
        "tags": [],
        "status": "Pendiente",
        "notes": "",
        "supplier": "",
        "estimated_cost": 0.0,
        "attachments": [],
        "characters": [],
        "locations": [],
        "favorite": False,
        "custom_fields": {},
        "created_at": now,
        "modified_at": now,
    }
    record.update(values)
    return record
