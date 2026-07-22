"""Safe UTF-8 input/output for CinePlan project files."""

import json
import os
import tempfile
from pathlib import Path

from project.project_validator import validate_project_container


class ProjectIOError(OSError):
    """An expected project filesystem or decoding failure."""


def write_project(path, container):
    """Atomically write a validated project container."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        validate_project_container(container)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(container, temporary, ensure_ascii=False, indent=4)
            temporary.flush()
            os.fsync(temporary.fileno())

        with temporary_path.open("r", encoding="utf-8") as saved_file:
            validate_project_container(json.load(saved_file))
        os.replace(temporary_path, destination)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise ProjectIOError("No se pudo guardar el proyecto.") from error


def read_json(path):
    try:
        with Path(path).open("r", encoding="utf-8-sig") as project_file:
            return json.load(project_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProjectIOError("No se pudo abrir el proyecto seleccionado.") from error


def read_project(path):
    return validate_project_container(read_json(path))
