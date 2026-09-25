"""The module registry: the only way the Core finds Specialty Modules (design doc §4.1).

Modules are named here as import paths and loaded by name, so no Core code imports a module; the
architecture test enforces that. Each module package exposes `MODULE`, a SpecialtyModule.
"""

import importlib
from functools import cache

from app.modules.registry.contract import SpecialtyModule

# Installed with this build. A migration registers each one in `specialty_module`.
INSTALLED: tuple[str, ...] = ("app.specialties.oncology",)


@cache
def installed_modules() -> dict[str, SpecialtyModule]:
    modules: dict[str, SpecialtyModule] = {}
    for path in INSTALLED:
        module = importlib.import_module(path).MODULE
        if not isinstance(module, SpecialtyModule):
            raise TypeError(f"{path}.MODULE is not a SpecialtyModule")
        if module.key in modules:
            raise ValueError(f"Two installed modules share the key {module.key!r}")
        modules[module.key] = module
    return modules
