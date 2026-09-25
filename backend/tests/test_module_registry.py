"""The Specialty Module contract, registry and Builder (design doc §4.1)."""

from app.core.permissions import CORE_FACT_RIGHTS
from app.modules.registry.builder import build
from app.modules.registry.contract import SpecialtyModule
from app.modules.registry.registry import installed_modules


def test_oncology_registers_through_the_contract() -> None:
    oncology = installed_modules()["oncology"]
    assert isinstance(oncology, SpecialtyModule)
    assert oncology.display_name == "Oncology"
    assert {"cancer_diagnosis", "biomarker"} <= set(oncology.verification_rights)
    assert "treatment-options" in {tab.segment for tab in oncology.patient_tabs}
    assert {s.slot for s in oncology.ui_sections} == {"patient-overview", "patient-summary", "clinical-data-tabs"}


def test_the_core_alone_builds_with_no_modules() -> None:
    config = build([])
    assert config.active_modules == ()
    assert config.verification_rights.fact_kinds() == set(CORE_FACT_RIGHTS)
    assert config.ui_sections == () and config.patient_tabs == ()


def test_the_builder_combines_the_core_with_active_modules() -> None:
    config = build(["oncology"])
    assert config.active_modules == ("oncology",)
    assert config.verification_rights.can_verify("clinician", "cancer_diagnosis")
    assert not config.verification_rights.can_verify("trial_coordinator", "cancer_diagnosis")
    assert config.verification_rights.can_verify("trial_coordinator", "lab_result")
    overview = [active.section.id for active in config.ui_sections if active.section.slot == "patient-overview"]
    assert overview == ["cancer-diagnoses"]


def test_an_unknown_module_is_ignored_rather_than_guessed() -> None:
    assert build(["cardiology"]).active_modules == ()
