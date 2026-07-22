"""Metadata for the official CinePlan project container."""

from datetime import datetime, timezone
from uuid import uuid4


FILE_TYPE = "CinePlan Scheduler Project"
PROJECT_EXTENSION = ".cps"
SCHEMA_VERSION = 1
CINEPLAN_VERSION = "3.0"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def build_metadata(existing=None):
    """Create save metadata while preserving project identity and creation time."""
    existing = existing or {}
    return {
        "file_type": FILE_TYPE,
        "extension": PROJECT_EXTENSION,
        "schema_version": SCHEMA_VERSION,
        "cineplan_version": CINEPLAN_VERSION,
        "project_id": existing.get("project_id") or str(uuid4()),
        "created_at": existing.get("created_at") or utc_now(),
        "last_saved": utc_now(),
    }
