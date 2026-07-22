"""Read models for resource catalogs and scene lists."""


def catalog_rows(engine, resource_type):
    rows = []
    for resource in engine.resources(resource_type):
        assignments = engine.assignments_for_resource(resource["id"])
        rows.append({
            "ID": resource["id"], "Nombre": resource.get("name", ""),
            "Categoría": resource.get("category", ""), "Estado": resource.get("status", ""),
            "Escenas": ", ".join(sorted({a["scene_id"] for a in assignments})),
            "Cantidad": sum(int(a.get("quantity", 1) or 0) for a in assignments),
            "Favorito": bool(resource.get("favorite")),
            "Creado": resource.get("created_at", ""), "Modificado": resource.get("modified_at", ""),
        })
    return rows
