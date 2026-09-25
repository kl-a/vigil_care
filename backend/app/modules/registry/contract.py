"""The Specialty Module contract (design doc §4.1, ADR 0004).

A Specialty Module declares what it contributes at each extension point. It may import the Core's
public interfaces; the Core never imports it (the registry loads it by name). Each contribution is a
self-contained unit so a concept can move between modules, or into the Core (portability rule).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from pydantic import BaseModel

from app.core.permissions import FactRight


@dataclass(frozen=True)
class UiSection:
    """A section the module adds to a Core screen's slot; the frontend supplies the renderer by `id`."""

    id: str
    slot: str
    title: str
    order: int


@dataclass(frozen=True)
class PatientTab:
    """A tab the module adds to the Patient screens."""

    segment: str
    label: str


@dataclass(frozen=True)
class DocumentTypeDefinition:
    """A Document Type the module can classify and extract (rows are added by its migrations)."""

    key: str
    display_name: str
    extraction_prompt_ref: str | None = None


@dataclass(frozen=True)
class SpecialtyModule:
    key: str
    display_name: str
    version: str
    # Clinical Record: fact kinds and the Pydantic schema of each (validated before write).
    fact_kinds: Mapping[str, type[BaseModel]] = field(default_factory=dict)
    document_types: Sequence[DocumentTypeDefinition] = ()
    # Verification rights: the module's rows of design doc §6.4.
    verification_rights: Mapping[str, FactRight] = field(default_factory=dict)
    ui_sections: Sequence[UiSection] = ()
    patient_tabs: Sequence[PatientTab] = ()
    # Trial matching: the criteria attributes this module evaluates.
    trial_vocabulary: Sequence[str] = ()
    # Treatment Options (optional): the key of the module's source, e.g. "eviq".
    treatment_option_source: str | None = None
    open_item_types: Sequence[str] = ()
