"""Tests for settings migration, CLI defaults, logging format, and tracing."""
from __future__ import annotations

import json
import logging
import tempfile
import unittest
from pathlib import Path

from main import build_argument_parser, parse_cli_arguments
from visualcpsa.exceptions import ConfigurationError
from visualcpsa.logging_config import configure_logging, get_logger, normalize_log_level, traced
from visualcpsa.settings import Settings


class SettingsLoggingTests(unittest.TestCase):
    """Verify concrete logging settings and class-aware log records."""

    def tearDown(self) -> None:
        """Close and remove handlers so temporary log paths cannot leak between tests."""
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            handler.close()
            root_logger.removeHandler(handler)

    def test_settings_migrates_missing_logging_keys(self) -> None:
        """Existing show_intro-only settings should be expanded and saved."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('{"show_intro": false}', encoding="utf-8")
            settings = Settings.load(path)
            migrated = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(settings.show_intro)
        self.assertEqual(settings.log_level, "INFO")
        self.assertEqual(settings.log_file, "vcpsa.log")
        self.assertEqual(set(migrated), {"show_intro", "log_level", "log_file"})

    def test_invalid_logging_level_raises(self) -> None:
        """Unsupported logging levels should raise ConfigurationError."""
        with self.assertRaises(ConfigurationError):
            normalize_log_level("verbose")

    def test_cli_defaults_come_from_settings(self) -> None:
        """Full CLI parser should use settings-based logging defaults."""
        settings = Settings(log_level="WARNING", log_file="custom.log")
        namespace = build_argument_parser(settings).parse_args([])
        self.assertEqual(namespace.log_level, "WARNING")
        self.assertEqual(namespace.log_file, "custom.log")

    def test_two_stage_cli_honors_config_defaults(self) -> None:
        """Two-stage parsing should load logging defaults from the selected settings file."""
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "settings.json"
            Settings(show_intro=False, log_level="ERROR", log_file="selected.log").save(settings_path)
            arguments, settings = parse_cli_arguments(["--config", str(settings_path)])
        self.assertEqual(arguments.log_level, "ERROR")
        self.assertTrue(str(arguments.log_file).endswith("selected.log"))
        self.assertEqual(settings.log_level, "ERROR")

    def test_log_records_include_required_context(self) -> None:
        """Configured records should contain date, file, class, function, line, and message."""
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "vcpsa.log"
            configure_logging("DEBUG", log_path)
            get_logger(self).info("context test")
            logging.shutdown()
            content = log_path.read_text(encoding="utf-8")
        self.assertIn("test_settings_logging.py", content)
        self.assertIn("SettingsLoggingTests", content)
        self.assertIn("test_log_records_include_required_context", content)
        self.assertIn("context test", content)

    def test_traced_logs_entry_and_exit(self) -> None:
        """The tracing decorator should log arguments and return values at DEBUG."""
        @traced
        def sample(value: int) -> int:
            """Return one more than value."""
            return value + 1
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "vcpsa.log"
            configure_logging("DEBUG", log_path)
            self.assertEqual(sample(2), 3)
            logging.shutdown()
            content = log_path.read_text(encoding="utf-8")
        self.assertIn("ENTER", content)
        self.assertIn("EXIT", content)
        self.assertIn("return=3", content)


if __name__ == "__main__":
    unittest.main()
