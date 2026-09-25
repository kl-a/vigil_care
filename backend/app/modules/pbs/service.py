"""PBS Drug Lookup (#20, design doc §5 screen 14): search the current PBS Schedule and read a drug's items.

Shows the items loaded by the latest Refresh that loaded any, so a failed Refresh leaves the previous
schedule visible. Staff only ("pbs_lookup"): the developer admin's navigation has no PBS lookup.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.audit.service import Actor
from app.core.permissions import require
from app.modules.pbs.models import PbsItem, PbsRefreshLog
from app.modules.pbs.schemas import (
    PbsDrug, PbsDrugRow, PbsItemView, PbsListingView, PbsRefreshView, PbsScheduleStatus,
)

SEARCH_LIMIT = 25


class DrugNotFound(LookupError):
    """No such item in the current schedule."""


def current_refresh(db: Session) -> PbsRefreshLog | None:
    """The latest Refresh that loaded any items: its items are the schedule Vigil shows."""
    query = (
        select(PbsRefreshLog)
        .where(PbsRefreshLog.status.in_(("succeeded", "partial")), PbsRefreshLog.item_count > 0)
        .order_by(PbsRefreshLog.refreshed_at.desc())
        .limit(1)
    )
    return db.scalars(query).first()


def _last_refresh(db: Session) -> PbsRefreshLog | None:
    return db.scalars(select(PbsRefreshLog).order_by(PbsRefreshLog.refreshed_at.desc()).limit(1)).first()


def _refresh_view(log: PbsRefreshLog | None) -> PbsRefreshView | None:
    if log is None:
        return None
    return PbsRefreshView(status=log.status, source=log.source, refreshed_at=log.refreshed_at, schedule_date=log.schedule_date)


def _money(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def schedule_status(db: Session, actor: Actor) -> PbsScheduleStatus:
    require(actor.job_title, "pbs_lookup")
    current = current_refresh(db)
    return PbsScheduleStatus(
        schedule_date=current.schedule_date if current else None,
        is_sample=current is not None and current.source == "sample",
        item_count=(current.item_count or 0) if current else 0,
        safety_net_general=_money(current.safety_net_general) if current else None,
        safety_net_concessional=_money(current.safety_net_concessional) if current else None,
        current=_refresh_view(current),
        last_refresh=_refresh_view(_last_refresh(db)),
    )


def search(db: Session, actor: Actor, q: str) -> list[PbsDrugRow]:
    """Every word of `q` matches the drug (its active ingredients), a brand or an item code."""
    require(actor.job_title, "pbs_lookup")
    current = current_refresh(db)
    words = q.split()
    if current is None or not words:
        return []
    query = select(PbsItem).where(PbsItem.refresh_log_id == current.id)
    for word in words:
        pattern = f"%{word}%"
        query = query.where(or_(
            PbsItem.drug_name.ilike(pattern),
            cast(PbsItem.brand_names, String).ilike(pattern),
            func.upper(PbsItem.item_code) == word.upper(),
        ))
    drugs: dict[str, list[PbsItem]] = {}
    for item in db.scalars(query.order_by(func.lower(PbsItem.drug_name), PbsItem.item_code)):
        drugs.setdefault(item.drug_name, []).append(item)
    return [
        PbsDrugRow(
            drug_name=name,
            brand_names=_brands(items),
            item_code=items[0].item_code,
            item_count=len(items),
        )
        for name, items in list(drugs.items())[:SEARCH_LIMIT]
    ]


def drug(db: Session, actor: Actor, item_code: str) -> PbsDrug:
    """The drug an item belongs to, with all its items in the current schedule."""
    require(actor.job_title, "pbs_lookup")
    current = current_refresh(db)
    if current is None:
        raise DrugNotFound()
    in_schedule = select(PbsItem).where(PbsItem.refresh_log_id == current.id)
    found = db.scalars(in_schedule.where(PbsItem.item_code == item_code.upper())).first()
    if found is None:
        raise DrugNotFound()
    items = list(db.scalars(in_schedule.where(PbsItem.drug_name == found.drug_name).order_by(PbsItem.item_code)))
    return PbsDrug(
        drug_name=found.drug_name,
        brand_names=_brands(items),
        schedule_date=found.schedule_date,
        items=[_item(item) for item in items],
    )


def _brands(items: list[PbsItem]) -> list[str]:
    return sorted({str(brand) for item in items for brand in item.brand_names})


def _item(item: PbsItem) -> PbsItemView:
    return PbsItemView(
        item_code=item.item_code,
        form=item.form,
        program_code=item.program_code,
        brand_names=[str(brand) for brand in item.brand_names],
        restriction_level=item.restriction_level,
        listings=[_listing(listing) for listing in item.indications],
        max_quantity=item.max_quantity,
        max_amount=_money(item.max_amount),
        amount_unit=item.amount_unit,
        repeats=item.repeats,
        copay_general=_money(item.patient_copay_general),
        copay_concessional=_money(item.patient_copay_concessional),
        schedule_date=item.schedule_date,
    )


def _listing(listing: dict[str, Any]) -> PbsListingView:
    return PbsListingView(
        indication=listing["indication"],
        treatment_phase=listing.get("treatment_phase"),
        level=listing["level"],
        restriction_code=listing["restriction_code"],
        conditions=list(listing.get("conditions", [])),
    )
