import datetime as dt

from pydantic import BaseModel


class PbsListingView(BaseModel):
    """An item's PBS Listing for one indication, with its prescribing conditions."""

    indication: str
    treatment_phase: str | None
    level: str  # unrestricted / restricted / authority_required / authority_required_streamlined
    restriction_code: str
    conditions: list[str]


class PbsOption(BaseModel):
    """A code and what to call it, e.g. a therapeutic group ("N", "Nervous system") or a PBS program."""

    code: str
    label: str


class PbsItemView(BaseModel):
    item_code: str
    form: str | None
    program_code: str | None
    program_title: str | None
    atc_codes: list[str]
    brand_names: list[str]
    restriction_level: str
    # Empty for an Unrestricted item: it's listed for any indication.
    listings: list[PbsListingView]
    # Per prescription: the most units (e.g. tablets) and packs; `pack_size` units come in a pack.
    max_quantity: int | None
    max_packs: int | None
    pack_size: int | None
    max_amount: float | None
    amount_unit: str | None
    repeats: int | None
    copay_general: float | None
    copay_concessional: float | None
    schedule_date: dt.date


class PbsDrugRow(BaseModel):
    """One drug in the list, summarising all its PBS Items in the current schedule."""

    drug_name: str
    brand_names: list[str]
    # Opens the drug (GET /pbs/drugs/{item_code}).
    item_code: str
    item_count: int
    # Its forms and strengths, e.g. "dexamfetamine sulfate 5 mg tablet, 100".
    forms: list[str]
    groups: list[PbsOption]
    # Every listing type across its items and their indications, least restrictive first.
    levels: list[str]


class PbsDrugPage(BaseModel):
    """A page of the drugs matching the filters, A–Z."""

    drugs: list[PbsDrugRow]
    total: int
    page: int
    page_size: int


class PbsFilters(BaseModel):
    """What the list can be filtered by, as found in the current schedule. `groups` starts with the Cancer
    drugs shortcut when there are any."""

    groups: list[PbsOption]
    programs: list[PbsOption]


class PbsDrug(BaseModel):
    drug_name: str
    brand_names: list[str]
    groups: list[PbsOption]
    schedule_date: dt.date
    items: list[PbsItemView]


class PbsRefreshView(BaseModel):
    status: str
    source: str
    refreshed_at: dt.datetime
    schedule_date: dt.date | None


class PbsScheduleStatus(BaseModel):
    """What the lookup shows: which schedule, where it came from, and whether the last Refresh failed."""

    schedule_date: dt.date | None
    is_sample: bool
    item_count: int
    safety_net_general: float | None
    safety_net_concessional: float | None
    # The Refresh whose items are shown; None until one has loaded any.
    current: PbsRefreshView | None
    # The most recent Refresh of any outcome.
    last_refresh: PbsRefreshView | None
