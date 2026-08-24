"""Recoverable JSON persistence for VisualCPSA projects."""
from __future__ import annotations

import json
import os
from pathlib import Path

from visualcpsa.exceptions import ModelInvariantError, PersistenceError
from visualcpsa.logging_config import traced
from visualcpsa.model import CPSAGraphicalProject


@traced
def save_project(project: CPSAGraphicalProject, path: str | Path) -> None:
    """Atomically save a project as JSON or raise PersistenceError."""
    if not isinstance(project, CPSAGraphicalProject):
        raise PersistenceError("save_project requires a CPSAGraphicalProject.")
    output_path = Path(path)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.write_text(json.dumps(project.to_dict(), indent=2) + "\n", encoding="utf-8")
        os.replace(temporary_path, output_path)
    except (OSError, UnicodeError, TypeError, ValueError) as error:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise PersistenceError(f"Could not save project to {output_path}: {error}") from error
    project.dirty = False
    if not output_path.exists():
        raise PersistenceError(f"Project file was not created at {output_path}.")


@traced
def load_project(path: str | Path) -> CPSAGraphicalProject:
    """Load a project from JSON or raise PersistenceError with the source path."""
    input_path = Path(path)
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
        project = CPSAGraphicalProject.from_dict(data)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, ModelInvariantError) as error:
        raise PersistenceError(f"Could not load project from {input_path}: {error}") from error
    project.dirty = False
    assert isinstance(project, CPSAGraphicalProject), "project load postcondition failed"
    return project
