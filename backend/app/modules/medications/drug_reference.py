"""The drug reference (#36, design doc §6.3): Shared Reference Data the Medication Manager picks from, built from
the schedule the PBS module shows. The PBS Refresh ends with this module's `step` (composed in `app/jobs.py`).
One row per PBS drug: its brands, most common ATC code (a cancer drug when any is L01/L02), and its PBS Items'
codes. A drug that leaves the Schedule stays (Medications may point at it) but is no longer offered.
"""

from collections import Counter
from collections.abc import Mapping
from typing import Any

from sqlalchemy import String, cast, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.audit.service import Actor
from app.core.jobs import JobContext
from app.core.permissions import require
from app.modules.medications.models import DrugReference
from app.modules.medications.schemas import DrugOption
from app.modules.pbs.schemas import ScheduleDrug
from app.modules.pbs.service import schedule_drugs

STEP = "drug_reference"
CANCER_ATC = ("L01", "L02")
SEARCH_LIMIT = 20


def step(ctx: JobContext) -> Mapping[str, Any]:
    """The PBS Refresh's last step: rebuild from the schedule now shown. Counts only (Support data)."""
    with ctx.sessions.begin() as db:
        return {"drug_count": rebuild(db)}


def rebuild(db: Session) -> int:
    """Returns how many drugs the schedule holds. Safe to run again: upserts on the generic name."""
    drugs = schedule_drugs(db)
    rows = [_row(drug) for drug in drugs]
    if rows:
        statement = insert(DrugReference).values(rows)
        db.execute(statement.on_conflict_do_update(
            index_elements=["generic_name"],
            set_={column: statement.excluded[column] for column in rows[0] if column != "generic_name"} | {"updated_at": func.now()},
        ))
    db.execute(
        update(DrugReference)
        .where(DrugReference.generic_name.not_in([drug.drug_name for drug in drugs]), DrugReference.in_current_schedule)
        .values(in_current_schedule=False, updated_at=func.now())
    )
    return len(rows)


def _row(drug: ScheduleDrug) -> dict[str, Any]:
    codes = Counter(drug.atc_codes)
    return {
        "generic_name": drug.drug_name,
        "brand_names": drug.brand_names,
        "atc_code": codes.most_common(1)[0][0] if codes else None,
        "is_cancer_drug": any(code.startswith(CANCER_ATC) for code in codes),
        "pbs_item_codes": drug.item_codes,
        "in_current_schedule": True,
    }


def search(db: Session, actor: Actor, q: str) -> list[DrugOption]:
    """Drugs in the current schedule whose generic or brand name contains every word of `q`, A–Z. Nothing for
    an empty query."""
    require(actor.job_title, "pbs_lookup")
    words = q.split()
    if not words:
        return []
    query = select(DrugReference).where(DrugReference.in_current_schedule)
    for word in words:
        pattern = f"%{word}%"
        query = query.where(or_(DrugReference.generic_name.ilike(pattern), cast(DrugReference.brand_names, String).ilike(pattern)))
    found = db.scalars(query.order_by(func.lower(DrugReference.generic_name)).limit(SEARCH_LIMIT))
    return [
        DrugOption(
            id=drug.id, generic_name=drug.generic_name, brand_names=[str(b) for b in drug.brand_names], atc_code=drug.atc_code,
            is_cancer_drug=drug.is_cancer_drug, pbs_item_codes=[str(code) for code in drug.pbs_item_codes],
        )
        for drug in found
    ]
