"""Per-Practice activation of Specialty Modules (design doc §4.1, §6.4) and the active configuration."""

import uuid
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.audit.service import Actor
from app.core.permissions import require
from app.modules.registry.builder import PracticeConfiguration, build
from app.modules.registry.models import PracticeModule
from app.modules.registry.registry import installed_modules
from app.modules.registry.schemas import (
    ActiveConfiguration,
    ActiveSectionOut,
    ActiveTabOut,
    ModuleChange,
    ModuleStatus,
)


class ModuleNotInstalled(LookupError):
    pass


def _activations(db: Session, practice_id: uuid.UUID) -> dict[str, PracticeModule]:
    rows = db.scalars(select(PracticeModule).where(PracticeModule.practice_id == practice_id))
    return {row.module_key: row for row in rows}


def active_module_keys(db: Session, practice_id: uuid.UUID) -> list[str]:
    return [key for key, row in _activations(db, practice_id).items() if row.is_active]


def configuration(db: Session, practice_id: uuid.UUID) -> PracticeConfiguration:
    """The Practice's configuration, assembled by the Builder from its active modules.

    For other Core modules (e.g. Verification rights for review). It returns the Builder's own immutable
    type, not a database model; the API's view of it is `active_configuration`.
    """
    return build(active_module_keys(db, practice_id))


def active_configuration(db: Session, actor: Actor) -> ActiveConfiguration:
    return as_api(configuration(db, actor.practice_id))


def as_api(config: PracticeConfiguration) -> ActiveConfiguration:
    """The API's view of a configuration: which modules, sections and Patient tabs the frontend shows."""
    return ActiveConfiguration(
        active_modules=list(config.active_modules),
        sections=[ActiveSectionOut(module=active.module, **asdict(active.section)) for active in config.ui_sections],
        patient_tabs=[ActiveTabOut(module=active.module, **asdict(active.tab)) for active in config.patient_tabs],
    )


def list_modules(db: Session, actor: Actor) -> list[ModuleStatus]:
    active = set(active_module_keys(db, actor.practice_id))
    return [
        ModuleStatus(key=module.key, display_name=module.display_name, version=module.version, is_active=module.key in active)
        for module in installed_modules().values()
    ]


def set_module_active(db: Session, actor: Actor, key: str, change: ModuleChange) -> ModuleStatus:
    """Deactivating hides the module's behaviour and UI; its data is kept, never deleted."""
    require(actor.job_title, "activate_modules", "Only a developer admin can switch Specialty Modules on or off.")
    module = installed_modules().get(key)
    if module is None:
        raise ModuleNotInstalled(f"No Specialty Module {key!r} is installed.")
    row = _activations(db, actor.practice_id).get(key)
    was_active = bool(row and row.is_active)
    if change.is_active != was_active:
        if row is None:
            row = PracticeModule(practice_id=actor.practice_id, module_key=key, is_active=change.is_active, changed_by_user_id=actor.id)
            db.add(row)
        else:
            row.is_active = change.is_active
            row.changed_by_user_id = actor.id
        db.flush()
        audit.record_verification(
            db,
            actor,
            subject_table="practice_module",
            subject_id=row.id,
            action="activate_module" if change.is_active else "deactivate_module",
            before={"is_active": was_active},
            after={"is_active": change.is_active},
            reason=(change.reason or "").strip() or None,
        )
    return ModuleStatus(key=module.key, display_name=module.display_name, version=module.version, is_active=change.is_active)
