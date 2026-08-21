"""VisualCPSA settings model and JSON persistence."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class Settings:
    """User settings loaded before the GUI appears."""

    show_intro: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize settings to a JSON-compatible dictionary."""
        data = asdict(self)
        assert isinstance(data["show_intro"], bool), "show_intro must serialize as bool"
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        """Deserialize settings from a dictionary, using defaults for missing keys."""
        assert isinstance(data, dict), "settings data must be a dictionary"
        settings = cls(show_intro=bool(data.get("show_intro", True)))
        assert isinstance(settings.show_intro, bool), "show_intro must be boolean"
        return settings

    @classmethod
    def load(cls, path: str | Path) -> "Settings":
        """Load settings from JSON, creating a default file if it does not exist."""
        settings_path = Path(path)
        if not settings_path.exists():
            settings = cls()
            settings.save(settings_path)
            return settings
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        settings = cls.from_dict(data)
        assert isinstance(settings, cls), "settings load failed"
        return settings

    def save(self, path: str | Path) -> None:
        """Save settings to JSON."""
        settings_path = Path(path)
        settings_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        assert settings_path.exists(), "settings file was not written"
