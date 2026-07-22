"""Validation rules for CinePlan project containers."""

from project.project_metadata import FILE_TYPE, PROJECT_EXTENSION, SCHEMA_VERSION


class ProjectValidationError(ValueError):
    """A friendly, expected project-file validation failure."""


def validate_project_container(data):
    if not isinstance(data, dict):
        raise ProjectValidationError(
            "El archivo seleccionado no es un Proyecto CinePlan válido."
        )
    if data.get("file_type") != FILE_TYPE or data.get("extension") != PROJECT_EXTENSION:
        raise ProjectValidationError(
            "El archivo seleccionado no es un Proyecto CinePlan válido."
        )
    if "schema_version" not in data:
        raise ProjectValidationError("El Proyecto CinePlan no indica una versión de formato.")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ProjectValidationError(
            "Esta versión del Proyecto CinePlan todavía no es compatible."
        )
    if not isinstance(data.get("project"), dict):
        raise ProjectValidationError("El Proyecto CinePlan no contiene datos de proyecto válidos.")
    return data
