"""Write the OpenAPI schema to backend/openapi.json for frontend type generation.

Usage (from backend/): uv run python -m app.scripts.export_openapi

The settings are built explicitly, so the export neither reads nor modifies the
process environment or backend/.env.
"""

import json
from pathlib import Path

from app.core.config import Settings, settings_from_values
from app.main import create_app

OUTPUT_PATH = Path(__file__).resolve().parents[2] / "openapi.json"

# Placeholder only: generating the schema never opens a database connection, but
# Settings requires a DATABASE_URL.
_PLACEHOLDER_DATABASE_URL = "postgresql+psycopg://openapi-export@localhost:5432/unused"


def build_export_settings() -> Settings:
    """Development settings (docs enabled) so the schema is always complete."""
    return settings_from_values(environment="development", database_url=_PLACEHOLDER_DATABASE_URL)


def main() -> None:
    schema = create_app(settings=build_export_settings()).openapi()
    text = json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    OUTPUT_PATH.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
