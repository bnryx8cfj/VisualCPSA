# VisualCPSA 0.1

VisualCPSA is a Python/Tkinter prototype for drawing CPSA protocol-flow diagrams and exporting CPSA-style S-expression syntax.

Target runtime: Python 3.10.7 on Windows 11.

No third-party packages are required at runtime.

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

## Splash screen

If `show_intro` is true in the settings file, a splash screen appears before the main window. The splash screen includes:

- a welcome banner,
- an announcement panel loaded from `announcements.md`,
- an animated GIF introduction,
- a `show introduction` checkbox,
- and a `Dismiss` button.
