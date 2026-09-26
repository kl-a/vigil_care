"""PBS Drug Lookup (#20, #30, design doc §5 screen 14): browse and filter every drug in the current PBS Schedule,
and read a drug's PBS Items.

Shows the items loaded by the latest Refresh that loaded any, so a failed Refresh leaves the previous
schedule visible. Staff only ("pbs_lookup"): the developer admin's navigation has no PBS lookup.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, String, cast, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, JSONPATH
from sqlalchemy.orm import Session

from app.audit.service import Actor
from app.core.permissions import require
from app.modules.pbs import atc
from app.modules.pbs.logs import current_log, last_log
from app.modules.pbs.models import RESTRICTION_LEVELS, PbsItem, PbsRefreshLog
from app.modules.pbs.schemas import (
    PbsDrug, PbsDrugPage, PbsDrugRow, PbsFilters, PbsItemView, PbsListingView, PbsOption, PbsRefreshView,
    PbsScheduleStatus,
)

PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


class DrugNotFound(LookupError):
    """No such item in the current schedule."""


class UnknownFilter(ValueError):
    """A therapeutic group or listing type Vigil doesn't know."""


@dataclass(frozen=True)
class DrugFilters:
    """Every word of `q` matches the drug (its active ingredients), a brand or an item code. `group` is an ATC
    top-level letter or "cancer"; `level` a listing type. A drug matches when any of its PBS Items does."""

    q: str = ""
    group: str | None = None
    program: str | None = None
    level: str | None = None


def _refresh_view(log: PbsRefreshLog | None) -> PbsRefreshView | None:
    if log is None:
        return None
    return PbsRefreshView(status=log.status, source=log.source, refreshed_at=log.refreshed_at, schedule_date=log.schedule_date)


def _money(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def schedule_status(db: Session, actor: Actor) -> PbsScheduleStatus:
    require(actor.job_title, "pbs_lookup")
    current = current_log(db)
    return PbsScheduleStatus(
        schedule_date=current.schedule_date if current else None,
        is_sample=current is not None and current.source == "sample",
        item_count=(current.item_count or 0) if current else 0,
        safety_net_general=_money(current.safety_net_general) if current else None,
        safety_net_concessional=_money(current.safety_net_concessional) if current else None,
        current=_refresh_view(current),
        last_refresh=_refresh_view(last_log(db)),
    )


def filters(db: Session, actor: Actor) -> PbsFilters:
    require(actor.job_title, "pbs_lookup")
    current = current_log(db)
    if current is None:
        return PbsFilters(groups=[], programs=[])
    in_schedule = PbsItem.refresh_log_id == current.id
    codes: set[str] = set(db.scalars(select(func.jsonb_array_elements_text(PbsItem.atc_codes)).where(in_schedule).distinct()))
    groups = [PbsOption(code=code, label=label) for code, label in atc.GROUPS.items() if any(c.startswith(code) for c in codes)]
    if any(c.startswith(atc.CANCER_PREFIXES) for c in codes):
        groups.insert(0, PbsOption(code=atc.CANCER, label=atc.CANCER_LABEL))
    programs = db.execute(
        select(PbsItem.program_code, func.max(PbsItem.program_title))
        .where(in_schedule, PbsItem.program_code.is_not(None))
        .group_by(PbsItem.program_code)
    )
    return PbsFilters(
        groups=groups,
        programs=sorted((PbsOption(code=str(code), label=str(title or code)) for code, title in programs), key=lambda p: p.label),
    )


def drugs(db: Session, actor: Actor, wanted: DrugFilters, page: int = 1, page_size: int = PAGE_SIZE) -> PbsDrugPage:
    """The drugs matching `wanted`, A–Z, `page_size` to a page (the first page is 1)."""
    require(actor.job_title, "pbs_lookup")
    page, page_size = max(page, 1), min(max(page_size, 1), MAX_PAGE_SIZE)
    current = current_log(db)
    if current is None:
        return PbsDrugPage(drugs=[], total=0, page=page, page_size=page_size)
    matching = select(PbsItem.drug_name).where(PbsItem.refresh_log_id == current.id, *_conditions(wanted)).group_by(PbsItem.drug_name)
    total = db.scalar(select(func.count()).select_from(matching.subquery())) or 0
    names = list(db.scalars(
        matching.order_by(func.lower(PbsItem.drug_name), PbsItem.drug_name).offset((page - 1) * page_size).limit(page_size)
    ))
    by_drug: dict[str, list[PbsItem]] = {name: [] for name in names}
    in_page = select(PbsItem).where(PbsItem.refresh_log_id == current.id, PbsItem.drug_name.in_(names))
    for item in db.scalars(in_page.order_by(PbsItem.item_code)):
        by_drug[item.drug_name].append(item)
    return PbsDrugPage(drugs=[_row(name, items) for name, items in by_drug.items()], total=total, page=page, page_size=page_size)


def drug(db: Session, actor: Actor, item_code: str) -> PbsDrug:
    """The drug an item belongs to, with all its items in the current schedule."""
    require(actor.job_title, "pbs_lookup")
    current = current_log(db)
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
        groups=_groups(items),
        schedule_date=found.schedule_date,
        items=[_item(item) for item in items],
    )


def _conditions(wanted: DrugFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    for word in wanted.q.split():
        pattern = f"%{word}%"
        conditions.append(or_(
            PbsItem.drug_name.ilike(pattern),
            cast(PbsItem.brand_names, String).ilike(pattern),
            func.upper(PbsItem.item_code) == word.upper(),
        ))
    if wanted.group:
        conditions.append(_in_group(wanted.group))
    if wanted.program:
        conditions.append(PbsItem.program_code == wanted.program)
    if wanted.level:
        if wanted.level not in RESTRICTION_LEVELS:
            raise UnknownFilter(wanted.level)
        conditions.append(or_(PbsItem.restriction_level == wanted.level, PbsItem.indications.contains([{"level": wanted.level}])))
    return conditions


def _in_group(group: str) -> ColumnElement[bool]:
    """Any of the item's ATC codes starts with the group's letter (or, for "cancer", with L01 or L02)."""
    if group == atc.CANCER:
        prefixes: tuple[str, ...] = atc.CANCER_PREFIXES
    elif group in atc.GROUPS:
        prefixes = (group,)
    else:
        raise UnknownFilter(group)
    path = "$[*] ? (" + " || ".join(f"@ starts with $p{i}" for i in range(len(prefixes))) + ")"
    variables = {f"p{i}": prefix for i, prefix in enumerate(prefixes)}
    return func.jsonb_path_exists(PbsItem.atc_codes, literal(path, JSONPATH), literal(variables, JSONB))


def _row(name: str, items: list[PbsItem]) -> PbsDrugRow:
    return PbsDrugRow(
        drug_name=name,
        brand_names=_brands(items),
        item_code=items[0].item_code,
        item_count=len(items),
        forms=sorted({item.form for item in items if item.form}),
        groups=_groups(items),
        levels=_levels(items),
    )


def _brands(items: list[PbsItem]) -> list[str]:
    return sorted({str(brand) for item in items for brand in item.brand_names})


def _groups(items: list[PbsItem]) -> list[PbsOption]:
    letters = sorted({str(code)[0] for item in items for code in item.atc_codes if code})
    return [PbsOption(code=letter, label=atc.label(letter)) for letter in letters]


def _levels(items: list[PbsItem]) -> list[str]:
    found = {item.restriction_level for item in items} | {listing["level"] for item in items for listing in item.indications}
    return [level for level in RESTRICTION_LEVELS if level in found]


def _item(item: PbsItem) -> PbsItemView:
    return PbsItemView(
        item_code=item.item_code,
        form=item.form,
        program_code=item.program_code,
        program_title=item.program_title,
        atc_codes=[str(code) for code in item.atc_codes],
        brand_names=[str(brand) for brand in item.brand_names],
        restriction_level=item.restriction_level,
        listings=[_listing(listing) for listing in item.indications],
        max_quantity=item.max_quantity,
        max_packs=item.max_packs,
        pack_size=item.pack_size,
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
