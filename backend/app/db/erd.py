"""Generate the clickable data-model diagram (docs/data-model/index.html) from the models.

    python -m app.db.erd            # rewrite docs/data-model/index.html
    python -m app.db.erd --check    # exit 1 if the committed file is out of date

The output is deterministic, so `make ci` can fail when the diagram is stale.
"""

import argparse
import json
import sys
from importlib import resources
from pathlib import Path
from typing import Any

from sqlalchemy import CheckConstraint, Column, Table, UniqueConstraint
from sqlalchemy.dialects import postgresql

from app.core.base_model import Entity, PracticeEntity, SupportEntity
from app.db.metadata import metadata

OUTPUT = Path(__file__).resolve().parents[3] / "docs" / "data-model" / "index.html"
PLACEHOLDER = "/*__VIGIL_DATA_MODEL__*/null"
POSTGRES = postgresql.dialect()  # type: ignore[no-untyped-call]

AREAS = {
    "practice": "Practice & Providers",
    "accounts": "Users",
    "patients": "Patients",
    "registry": "Specialty Modules",
    "documents": "Documents",
    "ocr": "OCR",
    "extraction": "Extraction & review",
    "audit": "Audit & support",
    "clinical": "Clinical Record",
    "medications": "Medications",
    "pbs": "PBS",
    "trials": "Trials",
    "matching": "Matching",
    "deid": "De-identification",
    "llm": "Cloud request ledger",
    "reports": "Reports & Exports",
    "orchestrator": "Jobs",
    "oncology": "Oncology",
}
STANDARD_COLUMNS = ("id", "created_at", "updated_at", "deleted_at", "deleted_by_user_id", "deleted_reason")


def _scope(model: type[Entity]) -> str:
    if issubclass(model, PracticeEntity):
        return "practice"
    if issubclass(model, SupportEntity):
        return "support"
    return "shared"


def _doc(model: type[Entity]) -> str:
    text = (model.__doc__ or "").strip()
    return " ".join(text.split("\n\n")[0].split())


def _column(column: Column[Any], targets: dict[str, str]) -> dict[str, Any]:
    default = column.server_default.arg if column.server_default is not None else None  # type: ignore[attr-defined]
    return {
        "name": column.name,
        "type": str(column.type.compile(dialect=POSTGRES)).lower(),
        "nullable": bool(column.nullable),
        "default": str(getattr(default, "text", default)) if default is not None else None,
        "allowed": list(column.info.get("allowed", ())),
        "references": targets.get(column.name),
        "standard": column.name in STANDARD_COLUMNS,
    }


def _table(table: Table, model: type[Entity]) -> dict[str, Any]:
    fks = sorted(table.foreign_key_constraints, key=lambda fk: (fk.column_keys, fk.referred_table.name))
    # Each column's target table; a composite FK is listed under its first column.
    targets = {fk.column_keys[0]: fk.referred_table.name for fk in fks}
    package = model.__module__.split(".")[-2]
    return {
        "name": table.name,
        "schema": table.schema,
        "module": "Oncology" if package == "oncology" else "Core",
        "area": AREAS[package],
        "scope": _scope(model),
        "immutable": bool(table.info.get("immutable")),
        "doc": _doc(model),
        "columns": [_column(c, targets) for c in table.columns],
        "foreignKeys": [
            {
                "columns": list(fk.column_keys),
                "table": fk.referred_table.name,
                "onDelete": fk.ondelete,
                "composite": len(fk.column_keys) > 1,
            }
            for fk in fks
        ],
        "checks": sorted(
            (
                {"name": str(c.name), "sql": str(c.sqltext)}
                for c in table.constraints
                if isinstance(c, CheckConstraint) and not str(c.name).endswith("_allowed")
            ),
            key=lambda c: c["name"],
        ),
        "uniques": sorted(
            [c.name for c in u.columns] for u in table.constraints if isinstance(u, UniqueConstraint)
        ),
        "indexes": sorted(
            (
                {
                    "name": str(i.name),
                    "on": [str(e) if not hasattr(e, "name") else e.name for e in i.expressions],
                    "unique": bool(i.unique),
                    "where": str(i.dialect_options["postgresql"]["where"])
                    if i.dialect_options["postgresql"]["where"] is not None
                    else None,
                    "using": i.dialect_options["postgresql"]["using"],
                }
                for i in table.indexes
            ),
            key=lambda i: i["name"],
        ),
    }


def data_model() -> list[dict[str, Any]]:
    models = {m.class_.__table__.name: m.class_ for m in Entity.registry.mappers}
    tables = [_table(t, models[t.name]) for t in metadata.tables.values()]
    order = list(AREAS.values())
    return sorted(tables, key=lambda t: (t["module"] != "Core", order.index(t["area"]), t["name"]))


def render() -> str:
    template = resources.files("app.db").joinpath("erd_template.html").read_text(encoding="utf-8")
    payload = json.dumps(data_model(), indent=1, sort_keys=True).replace("</", "<\\/")
    return template.replace(PLACEHOLDER, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the committed diagram is stale")
    args = parser.parse_args()
    html = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != html:
            sys.exit(f"{OUTPUT} is out of date. Run `make erd` and commit the result.")
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
