"""Smart resource lookup shared by future Breakdown modules."""


def autocomplete(engine, query, resource_type, limit=8):
    query = str(query or "").strip()
    if not query:
        return []
    results = engine.find(query, resource_type=resource_type)
    return [{
        **resource,
        "scenes": sorted({a["scene_id"] for a in engine.assignments_for_resource(resource["id"])}),
        "already_exists": True,
    } for resource in results[:limit]]
