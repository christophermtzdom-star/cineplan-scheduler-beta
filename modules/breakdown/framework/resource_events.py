"""Append-only resource events, ready for activity history and undo metadata."""

from copy import deepcopy

from .resource_models import utc_now


def append_event(store, event_type, resource_id, scene_id="", changes=None):
    event = {
        "type": event_type,
        "resource_id": resource_id,
        "scene_id": str(scene_id or ""),
        "timestamp": utc_now(),
        "changes": deepcopy(changes or {}),
    }
    store.setdefault("events", []).append(event)
    return event
