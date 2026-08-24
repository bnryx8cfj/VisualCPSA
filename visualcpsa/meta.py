"""Application metadata and validated resource paths for VisualCPSA."""
from __future__ import annotations

from pathlib import Path

from visualcpsa import __program_name__, __release_date__, __version__
from visualcpsa.exceptions import ResourceError
from visualcpsa.logging_config import traced

PROGRAM_NAME = __program_name__
VERSION = __version__
RELEASE_DATE = __release_date__
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PACKAGE_ROOT / "docs"
ASSETS_DIR = PACKAGE_ROOT / "assets"
REFERENCES_HTML = DOCS_DIR / "references.html"
DOCUMENTATION_HTML = DOCS_DIR / "documentation.html"
ANNOUNCEMENTS_MD = PACKAGE_ROOT / "announcements.md"
ICON_PATH = PACKAGE_ROOT / "VCPSA.ico"


@traced
def file_url(path: Path) -> str:
    """Return a browser-openable file URL or raise ResourceError if the resource is absent."""
    if not isinstance(path, Path):
        raise ResourceError("Resource path must be represented by pathlib.Path.")
    if not path.exists():
        raise ResourceError(f"Resource does not exist: {path}")
    url = path.resolve().as_uri()
    assert url.startswith("file:"), "file URL postcondition failed"
    return url
