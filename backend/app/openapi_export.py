"""Write the OpenAPI schema to stdout, for generating frontend types (make api-types)."""

import json
import sys

from app.core.config import Settings
from app.main import create_app


def main() -> None:
    # Include the dev-only routes so the frontend has their types; the server registers them only in dev.
    app = create_app(Settings(environment="dev", dev_login_enabled=True), database_check=lambda: True)
    json.dump(app.openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
