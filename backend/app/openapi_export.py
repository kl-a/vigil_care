"""Write the OpenAPI schema to stdout, for generating frontend types (make api-types)."""

import json
import sys

from app.core.config import Settings
from app.main import create_app


def main() -> None:
    app = create_app(Settings(environment="dev", dev_login_enabled=False), database_check=lambda: True)
    json.dump(app.openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
