"""Typed command-line entry point and logging bootstrap for VisualCPSA."""
from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from visualcpsa.exceptions import ConfigurationError, VisualCPSAError
from visualcpsa.logging_config import configure_logging, traced
from visualcpsa.settings import Settings


@dataclass(frozen=True)
class CLIArguments:
    """Resolved, concrete command-line values used to start VisualCPSA."""

    config: Path
    log_level: str
    log_file: Path


@traced
def build_bootstrap_parser() -> argparse.ArgumentParser:
    """Create the first-stage parser used to locate the settings file."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", default=str(Path.cwd() / "visualcpsa_settings.json"))
    assert isinstance(parser, argparse.ArgumentParser), "bootstrap parser construction failed"
    return parser


@traced
def build_argument_parser(settings: Settings) -> argparse.ArgumentParser:
    """Create the full parser using settings as effective CLI defaults."""
    if not isinstance(settings, Settings):
        raise ConfigurationError("build_argument_parser requires Settings.")
    parser = argparse.ArgumentParser(description="VisualCPSA graphical CPSA protocol editor.")
    parser.add_argument("--config", default=str(Path.cwd() / "visualcpsa_settings.json"), help="Settings JSON path.")
    parser.add_argument("--log-level", default=settings.log_level, choices=sorted({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}))
    parser.add_argument("--log-file", default=settings.log_file, help="Log file path; relative paths use the current working directory.")
    assert isinstance(parser, argparse.ArgumentParser), "argument parser construction failed"
    return parser


@traced
def parse_cli_arguments(arguments: list[str]) -> tuple[CLIArguments, Settings]:
    """Parse CLI in two stages so settings can define logging argument defaults."""
    if not isinstance(arguments, list) or not all(isinstance(argument, str) for argument in arguments):
        raise ConfigurationError(f"Command-line arguments must be a list of strings not {arguments!r}.")
    bootstrap_namespace, _ = build_bootstrap_parser().parse_known_args(arguments)
    config_path = Path(bootstrap_namespace.config)
    settings = Settings.load(config_path)
    namespace = build_argument_parser(settings).parse_args(arguments)
    log_file = Path(namespace.log_file)
    if not log_file.is_absolute():
        log_file = Path.cwd() / log_file
    resolved = CLIArguments(config=Path(namespace.config), log_level=namespace.log_level, log_file=log_file)
    assert resolved.config == config_path, "config path changed between parser stages"
    return resolved, settings


@traced
def run(arguments: list[str]) -> int:
    """Configure logging, start the GUI, and return an operating-system exit status."""
    try:
        cli_arguments, settings = parse_cli_arguments(arguments)
        configure_logging(cli_arguments.log_level, cli_arguments.log_file)
        settings.log_level = cli_arguments.log_level
        settings.log_file = str(cli_arguments.log_file)
        settings.save(cli_arguments.config)
        from visualcpsa.gui.app import VisualCPSAApp
        application = VisualCPSAApp(settings=settings, config_path=cli_arguments.config)
        application.mainloop()
        return 0
    except ConfigurationError as error:
        print(f"VisualCPSA configuration error: {error}", file=sys.stderr)
        return 2
    except VisualCPSAError as error:
        logging.getLogger(__name__).exception("Recoverable VisualCPSA startup failure")
        print(f"VisualCPSA could not start: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        logging.getLogger(__name__).exception("Unexpected VisualCPSA startup failure")
        print(f"Unexpected VisualCPSA failure: {error}", file=sys.stderr)
        return 1


def main() -> None:
    """Run VisualCPSA and terminate with the returned exit status."""
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
