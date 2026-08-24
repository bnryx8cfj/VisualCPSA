"""VisualCPSA settings model, migration, and JSON persistence."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from visualcpsa.exceptions import ConfigurationError
from visualcpsa.logging_config import normalize_log_level, traced

LOGGER = logging.getLogger(__name__)


@dataclass
class Settings:
    """User settings loaded before the GUI appears."""

    show_intro: bool = True
    log_level: str = "INFO"
    log_file: str = "vcpsa.log"

    def __post_init__(self) -> None:
        """Validate settings invariants after construction."""
        if not isinstance(self.show_intro, bool):
            raise ConfigurationError("show_intro must be a Boolean value.")
        self.log_level = normalize_log_level(self.log_level)
        if not isinstance(self.log_file, str) or not self.log_file.strip():
            raise ConfigurationError("log_file must be a non-empty string.")
        self.log_file = self.log_file.strip()

    @traced
    def to_dict(self) -> dict[str, Any]:
        """Serialize settings to a JSON-compatible dictionary."""
        data = asdict(self)
        assert set(data) == {"show_intro", "log_level", "log_file"}, "settings serialization keys changed"
        return data

    @classmethod
    @traced
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        """Deserialize settings and apply defaults to missing logging keys."""
        if not isinstance(data, dict):
            raise ConfigurationError("Settings JSON root must be an object.")
        show_intro = data.get("show_intro", True)
        log_level = data.get("log_level", "INFO")
        log_file = data.get("log_file", "vcpsa.log")
        if not isinstance(show_intro, bool) or not isinstance(log_level, str) or not isinstance(log_file, str):
            raise ConfigurationError("Settings values have invalid types.")
        settings = cls(show_intro=show_intro, log_level=log_level, log_file=log_file)
        assert isinstance(settings, cls), "settings deserialization failed"
        return settings

    @classmethod
    @traced
    def load(cls, path: str | Path) -> "Settings":
        """Load settings, create defaults when absent, and migrate missing logging keys."""
        settings_path = Path(path)
        if not settings_path.exists():
            settings = cls()
            settings.save(settings_path)
            return settings
        try:
            raw_data = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ConfigurationError(f"Could not load settings from {settings_path}: {error}") from error
        settings = cls.from_dict(raw_data)
        if set(raw_data) != {"show_intro", "log_level", "log_file"}:
            settings.save(settings_path)
        assert settings_path.exists(), "settings path must exist after loading"
        return settings

    @traced
    def save(self, path: str | Path) -> None:
        """Save settings to JSON and raise ConfigurationError on a recoverable file failure."""
        settings_path = Path(path)
        try:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        except (OSError, UnicodeError, TypeError) as error:
            raise ConfigurationError(f"Could not save settings to {settings_path}: {error}") from error
        if not settings_path.exists():
            raise ConfigurationError(f"Settings file was not created at {settings_path}.")
