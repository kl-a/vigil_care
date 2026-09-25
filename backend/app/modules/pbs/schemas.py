import datetime as dt

from pydantic import BaseModel


class PbsListingView(BaseModel):
    """An item's PBS Listing for one indication, with its prescribing conditions."""

    indication: str
    treatment_phase: str | None
    level: str  # unrestricted / restricted / authority_required / authority_required_streamlined
    restriction_code: str
    conditions: list[str]


class PbsItemView(BaseModel):
    item_code: str
    form: str | None
    program_code: str | None
    brand_names: list[str]
    restriction_level: str
    # Empty for an Unrestricted item: it's listed for any indication.
    listings: list[PbsListingView]
    max_quantity: int | None
    max_amount: float | None
    amount_unit: str | None
    repeats: int | None
    copay_general: float | None
    copay_concessional: float | None
    schedule_date: dt.date


class PbsDrugRow(BaseModel):
    """A search result: one drug and its items in the current schedule."""

    drug_name: str
    brand_names: list[str]
    # Opens the drug (GET /pbs/drugs/{item_code}).
    item_code: str
    item_count: int


class PbsDrug(BaseModel):
    drug_name: str
    brand_names: list[str]
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
