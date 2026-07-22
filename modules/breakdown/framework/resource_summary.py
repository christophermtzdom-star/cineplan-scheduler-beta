"""Workspace statistics shared across resource modules."""


def resource_statistics(engine, resource_type, scene_id):
    resources = engine.resources(resource_type)
    assignments = engine.assignments_for_scene(scene_id, resource_type)
    return {"current_scene": len(assignments), "project_total": len(resources),
            "favorites": sum(bool(r.get("favorite")) for r in resources)}
