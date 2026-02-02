from pathlib import Path

# .../setara3/app
APP_DIR = Path(__file__).resolve().parents[1]

# .../setara3/app/templates
TEMPLATES_DIR = APP_DIR / "templates"

# .../setara3/app/static
STATIC_DIR = APP_DIR / "static"
