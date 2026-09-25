from app.db import erd


def test_the_committed_data_model_diagram_is_up_to_date() -> None:
    assert erd.OUTPUT.read_text(encoding="utf-8") == erd.render(), (
        "docs/data-model/index.html is stale. Run `make erd` and commit it (CLAUDE.md: database changes)."
    )


def test_every_table_is_in_the_diagram() -> None:
    names = {t["name"] for t in erd.data_model()}
    assert len(names) == 61
    assert {"patient", "cancer_diagnosis", "job_kind"} <= names
