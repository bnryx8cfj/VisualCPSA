"""JSON persistence for VisualCPSA projects."""
from __future__ import annotations
import json
from pathlib import Path
from .model import CPSAGraphicalProject


def save_project(project: CPSAGraphicalProject, path: str | Path) -> None:
    """Save a project as JSON."""
    assert isinstance(project, CPSAGraphicalProject), "project must be CPSAGraphicalProject"
    output_path = Path(path)
    output_path.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")
    project.dirty = False


def load_project(path: str | Path) -> CPSAGraphicalProject:
    """Load a project from JSON."""
    input_path = Path(path)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    project = CPSAGraphicalProject.from_dict(data)
    project.dirty = False
    return project
