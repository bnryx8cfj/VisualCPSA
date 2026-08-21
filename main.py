"""Command-line entry point for VisualCPSA."""
from __future__ import annotations

import argparse
from pathlib import Path

from visualcpsa.settings import Settings


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the VisualCPSA command-line argument parser."""
    parser = argparse.ArgumentParser(description="VisualCPSA graphical CPSA protocol editor.")
    parser.add_argument(
        "--config",
        default=str(Path.cwd() / "visualcpsa_settings.json"),
        help="Path to the VisualCPSA settings JSON file. Defaults to visualcpsa_settings.json in the current working directory.",
    )
    assert isinstance(parser, argparse.ArgumentParser), "argument parser construction failed"
    return parser


def main() -> None:
    """Parse command-line arguments, load settings, and run the application."""
    parser = build_argument_parser()
    arguments = parser.parse_args()
    config_path = Path(arguments.config)
    settings = Settings.load(config_path)
    from visualcpsa.gui.app import VisualCPSAApp
    application = VisualCPSAApp(settings=settings, config_path=config_path)
    assert application is not None, "application construction failed"
    application.mainloop()


if __name__ == "__main__":
    main()
