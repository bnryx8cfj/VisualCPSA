"""Application metadata and resource paths for VisualCPSA."""
from __future__ import annotations
from pathlib import Path

from visualcpsa import __program_name__, __release_date__, __version__

PROGRAM_NAME = __program_name__
VERSION = __version__
RELEASE_DATE = __release_date__
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PACKAGE_ROOT / "docs"
ASSETS_DIR = PACKAGE_ROOT / "assets"
REFERENCES_HTML = DOCS_DIR / "references.html"
DOCUMENTATION_HTML = DOCS_DIR / "documentation.html"
SPLASH_GIF = ASSETS_DIR / "splash_needham_schroeder.gif"
ANNOUNCEMENTS_MD = PACKAGE_ROOT / "announcements.md"


def file_url(path: Path) -> str:
    """Return a browser-openable file URL for a local path."""
    assert isinstance(path, Path), "path must be a pathlib.Path"
    resolved_path = path.resolve()
    url = resolved_path.as_uri()
    assert url.startswith("file:"), "file URL must use the file scheme"
    return url
