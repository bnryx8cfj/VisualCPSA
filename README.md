# VisualCPSA 0.2

VisualCPSA is a Python/Tkinter prototype for drawing CPSA protocol-flow diagrams and exporting CPSA-style S-expression syntax.

Target runtime: Python 3.10.7 on Windows 11.

No third-party packages are required at runtime.

## Usage

```sh
python .\main.py --help
usage: main.py [-h] [--config CONFIG]

VisualCPSA graphical CPSA protocol editor.

options:
  -h, --help       show this help message and exit
  --config CONFIG  Path to the VisualCPSA settings JSON file. Defaults to visualcpsa_settings.json in the current working directory.
```

## Command line

```bat
python main.py --config visualcpsa_settings.json
```

If `--config` is omitted, VisualCPSA looks for `visualcpsa_settings.json` in the current working directory.

## Setup

```bat
create_venv.bat
activate_venv.bat
run_tests.bat
run_app.bat
```

## VisualCPSA Model and CPSA Export Unit Tests

Run with Python 3.10.7:

```bat
python -m unittest discover -s tests -v
```

The suite tests:
- the permissive editor representation
- JSON round trips
- global message ordering
- paired send/receive generation
- Needham-Schroeder trace order
- separation of display markup from raw CPSA syntax.

## Splash screen

If `show_intro` is true in the settings file, a splash screen appears before the main window. The splash screen includes:

- a welcome banner,
- an announcement panel loaded from `announcements.md`,
- an animated GIF introduction,
- a `show introduction` checkbox,
- and a `Dismiss` button.
