"""Generic project-level Master Resource Engine.

Resources are owned once by the project. Scene records are assignments containing
only assignment-specific values and a stable resource ID.
"""

from collections.abc import Mapping
from copy import deepcopy

from .resource_events import append_event
from .resource_models import empty_store, new_resource, utc_now


class ResourceConflictError(ValueError):
    pass


class ResourceNotFoundError(KeyError):
    pass


class MasterResourceEngine:
    def __init__(self, store=None):
        self.store = store if isinstance(store, dict) else empty_store()
        defaults = empty_store()
        for key, value in defaults.items():
            if not isinstance(self.store.get(key), type(value)):
                self.store[key] = value

    def _next_id(self, prefix):
        current = int(self.store["sequences"].get(prefix, 0))
        resources = self.store["resources"]
        while True:
            current += 1
            candidate = f"{prefix}-{current:04d}"
            if candidate not in resources:
                self.store["sequences"][prefix] = current
                return candidate

    def resources(self, resource_type=None):
        values = self.store["resources"].values()
        if resource_type:
            values = (r for r in values if r.get("resource_type") == resource_type)
        return [deepcopy(r) for r in values]

    def get(self, resource_id):
        try:
            return deepcopy(self.store["resources"][resource_id])
        except KeyError as error:
            raise ResourceNotFoundError(resource_id) from error

    def find(self, query="", resource_type=None, category=None, status=None):
        terms = str(query or "").casefold().split()
        matches = []
        for resource in self.resources(resource_type):
            if category and resource.get("category") != category:
                continue
            if status and resource.get("status") != status:
                continue
            assignments = self.assignments_for_resource(resource["id"])
            haystack = " ".join(str(value) for value in (
                resource.get("name"), resource.get("category"), resource.get("status"),
                " ".join(resource.get("tags", [])), " ".join(resource.get("characters", [])),
                " ".join(a.get("scene_id", "") for a in assignments),
            )).casefold()
            if all(term in haystack for term in terms):
                matches.append(resource)
        return matches

    def exact_name(self, name, resource_type, category=None):
        identity = str(name or "").strip().casefold()
        return next((r for r in self.resources(resource_type)
                     if r.get("name", "").casefold() == identity
                     and (not category or r.get("category") == category)), None)

    def create(self, config, name, category, allow_duplicate=False, **values):
        existing = self.exact_name(name, config.resource_type, category)
        if existing and not allow_duplicate:
            raise ResourceConflictError(existing["id"])
        resource_id = self._next_id(config.id_prefix)
        resource = new_resource(resource_id, config.resource_type, name, category, **values)
        self.store["resources"][resource_id] = resource
        append_event(self.store, "resource_created", resource_id, changes=resource)
        return deepcopy(resource)

    def update(self, resource_id, **changes):
        resource = self.store["resources"].get(resource_id)
        if resource is None:
            raise ResourceNotFoundError(resource_id)
        immutable = {"id", "resource_type", "created_at"}
        applied = {key: deepcopy(value) for key, value in changes.items() if key not in immutable}
        resource.update(applied)
        resource["modified_at"] = utc_now()
        append_event(self.store, "resource_updated", resource_id, changes=applied)
        return deepcopy(resource)

    def assign(self, resource_id, scene_id, **values):
        if resource_id not in self.store["resources"]:
            raise ResourceNotFoundError(resource_id)
        scene_id = str(scene_id)
        assignments = self.store["assignments"].setdefault(scene_id, [])
        assignment = next((a for a in assignments if a.get("resource_id") == resource_id), None)
        event = "resource_reused" if self.assignments_for_resource(resource_id) else "resource_assigned"
        if assignment is None:
            assignment = {"resource_id": resource_id, "scene_id": scene_id, "quantity": 1}
            assignments.append(assignment)
        assignment.update(deepcopy(values))
        assignment["resource_id"] = resource_id
        assignment["scene_id"] = scene_id
        append_event(self.store, event, resource_id, scene_id, values)
        self._refresh_relationships(resource_id)
        return deepcopy(assignment)

    def unassign(self, resource_id, scene_id):
        scene_id = str(scene_id)
        assignments = self.store["assignments"].get(scene_id, [])
        self.store["assignments"][scene_id] = [
            a for a in assignments if a.get("resource_id") != resource_id
        ]
        append_event(self.store, "resource_unassigned", resource_id, scene_id)
        self._refresh_relationships(resource_id)

    def delete(self, resource_id):
        if resource_id not in self.store["resources"]:
            raise ResourceNotFoundError(resource_id)
        for scene_id in list(self.store["assignments"]):
            self.store["assignments"][scene_id] = [
                a for a in self.store["assignments"][scene_id]
                if a.get("resource_id") != resource_id
            ]
        del self.store["resources"][resource_id]
        append_event(self.store, "resource_deleted", resource_id)

    def assignments_for_scene(self, scene_id, resource_type=None):
        rows = deepcopy(self.store["assignments"].get(str(scene_id), []))
        if resource_type:
            rows = [a for a in rows if self.store["resources"].get(
                a.get("resource_id"), {}).get("resource_type") == resource_type]
        return rows

    def assignments_for_resource(self, resource_id):
        return [deepcopy(a) for values in self.store["assignments"].values()
                for a in values if a.get("resource_id") == resource_id]

    def _refresh_relationships(self, resource_id):
        resource = self.store["resources"].get(resource_id)
        if resource is None:
            return
        assignments = self.assignments_for_resource(resource_id)
        resource["characters"] = sorted({str(a.get("character", "")).strip()
                                          for a in assignments if a.get("character")})
        resource["locations"] = sorted({str(a.get("location", "")).strip()
                                         for a in assignments if a.get("location")})
        resource["modified_at"] = utc_now()

    def snapshot(self):
        return deepcopy(self.store)
