"""The Builder: one Practice's active configuration, assembled from the Core and its active modules (§4.1)."""

from collections.abc import Iterable
from dataclasses import dataclass

from app.core.permissions import CORE_FACT_RIGHTS, VerificationRights
from pydantic import BaseModel

from app.modules.registry.contract import DocumentTypeDefinition, PatientTab, SpecialtyModule, UiSection
from app.modules.registry.registry import installed_modules


@dataclass(frozen=True)
class ActiveSection:
    module: str
    section: UiSection


@dataclass(frozen=True)
class ActiveTab:
    module: str
    tab: PatientTab


@dataclass(frozen=True)
class PracticeConfiguration:
    """Every extension point of §4.1, combined for one Practice."""

    active_modules: tuple[str, ...]
    fact_kinds: dict[str, type[BaseModel]]
    condition_extensions: dict[str, str]
    document_types: tuple[DocumentTypeDefinition, ...]
    verification_rights: VerificationRights
    ui_sections: tuple[ActiveSection, ...]
    patient_tabs: tuple[ActiveTab, ...]
    trial_vocabulary: tuple[str, ...]
    treatment_option_sources: dict[str, str]
    open_item_types: tuple[str, ...]


def build(active_keys: Iterable[str], installed: dict[str, SpecialtyModule] | None = None) -> PracticeConfiguration:
    """Keys that aren't installed are ignored: a module missing from this build contributes nothing."""
    installed = installed if installed is not None else installed_modules()
    wanted = set(active_keys)
    modules = [module for key, module in installed.items() if key in wanted]
    rights = dict(CORE_FACT_RIGHTS)
    for module in modules:
        rights.update(module.verification_rights)
    return PracticeConfiguration(
        active_modules=tuple(module.key for module in modules),
        fact_kinds={kind: schema for module in modules for kind, schema in module.fact_kinds.items()},
        condition_extensions={module.key: module.condition_extension for module in modules if module.condition_extension},
        document_types=tuple(doc for module in modules for doc in module.document_types),
        verification_rights=VerificationRights(rights),
        ui_sections=tuple(
            sorted(
                (ActiveSection(module.key, section) for module in modules for section in module.ui_sections),
                key=lambda active: (active.section.slot, active.section.order),
            )
        ),
        patient_tabs=tuple(ActiveTab(module.key, tab) for module in modules for tab in module.patient_tabs),
        trial_vocabulary=tuple(term for module in modules for term in module.trial_vocabulary),
        treatment_option_sources={
            module.key: module.treatment_option_source for module in modules if module.treatment_option_source
        },
        open_item_types=tuple(kind for module in modules for kind in module.open_item_types),
    )
