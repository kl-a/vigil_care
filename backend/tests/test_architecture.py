"""Module boundaries (design doc §4.1, §14; ADR 0004), checked on the source itself."""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
SPECIALTIES = APP / "specialties"
# Tooling that must see every table (Alembic metadata, the data-model diagram) is the documented exception.
TOOLING = {APP / "db" / "metadata.py"}


def imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def specialty_of(module: str) -> str | None:
    parts = module.split(".")
    return parts[2] if parts[:2] == ["app", "specialties"] and len(parts) > 2 else None


def test_the_core_never_imports_a_specialty_module() -> None:
    offenders = {
        f"{path.relative_to(APP)} imports {name}"
        for path in APP.rglob("*.py")
        if SPECIALTIES not in path.parents and path not in TOOLING
        for name in imports(path)
        if name == "app.specialties" or specialty_of(name)
    }
    assert offenders == set()


def test_specialty_modules_never_import_each_other() -> None:
    offenders = set()
    for package in (p for p in SPECIALTIES.iterdir() if p.is_dir() and (p / "__init__.py").exists()):
        for path in package.rglob("*.py"):
            for name in imports(path):
                other = specialty_of(name)
                if other and other != package.name:
                    offenders.add(f"{path.relative_to(APP)} imports {name}")
    assert offenders == set()


def test_the_architecture_test_would_catch_a_core_import(tmp_path: Path) -> None:
    sneaky = tmp_path / "sneaky.py"
    sneaky.write_text("from app.specialties.oncology import MODULE\n")
    assert specialty_of(next(iter(imports(sneaky)))) == "oncology"
