"""The PBS Refresh (#19, design doc §10.2): Job Kind `refresh_pbs`, monthly on the 1st or started by a
developer admin. Each attempt writes a `pbs_refresh_log` row: succeeded, partial or failed.

- `fetch` asks the PBS Schedule API which schedule is current. If the API can't be reached: with a schedule
  from the API already loaded, the attempt fails and that schedule stays visible; with none, the bundled
  sample is used instead (partial, marked as sample data), so demos work offline.
- `store` fetches the schedule's oncology-relevant items and stores them, with their log row, in one
  transaction. Items are upserted on (item code, schedule date), so running it again is safe.
"""

from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.pbs.api_client import HttpTransport, PbsApiClient
from app.modules.pbs.models import PbsItem, PbsRefreshLog
from app.modules.pbs.sample import SampleSchedule
from app.modules.pbs.schedule import Schedule as PbsSchedule
from app.modules.pbs.schedule import ScheduleRef, ScheduleSource, SourceUnreachable
from app.modules.pbs.service import current_refresh
from app.orchestrator.handlers import JobContext, JobFailed, JobHandler, Schedule, monthly

KIND = "refresh_pbs"
MONTHLY = Schedule(KIND, due=monthly(day=1))
BATCH = 500

SourceFactory = Callable[[Settings], ScheduleSource]


def api_source(settings: Settings) -> ScheduleSource:
    return PbsApiClient(HttpTransport(settings.pbs_api_url, settings.pbs_api_key, settings.pbs_api_min_interval))


def sample_source(settings: Settings) -> ScheduleSource:
    return SampleSchedule()


def handler(api: SourceFactory = api_source, sample: SourceFactory = sample_source) -> JobHandler:
    """Tests pass an `api` that replays a recorded fixture."""

    def fetch(ctx: JobContext) -> Mapping[str, Any]:
        try:
            ref = api(ctx.settings).current()
        except SourceUnreachable as unreachable:
            with ctx.sessions.begin() as db:
                current = current_refresh(db)
                keep_current = current is not None and current.source == "pbs_api"
                if keep_current:
                    _log_failure(db, unreachable.code)
            if keep_current:
                raise JobFailed(unreachable.code) from None
            ref = sample(ctx.settings).current()
            return {"source": "sample", "schedule_date": ref.schedule_date.isoformat(), "reason": unreachable.code}
        return {"source": "pbs_api", "schedule_code": ref.schedule_code, "schedule_date": ref.schedule_date.isoformat()}

    def store(ctx: JobContext) -> Mapping[str, Any]:
        found = ctx.outputs["fetch"]
        source = api(ctx.settings) if found["source"] == "pbs_api" else sample(ctx.settings)
        ref = ScheduleRef(schedule_code=int(found.get("schedule_code") or 0), schedule_date=date.fromisoformat(found["schedule_date"]))
        try:
            schedule = source.fetch(ref)
        except SourceUnreachable as unreachable:
            with ctx.sessions.begin() as db:
                _log_failure(db, unreachable.code, ref.schedule_date)
            raise JobFailed(unreachable.code) from None
        with ctx.sessions.begin() as db:
            log = _store(db, schedule, reason=found.get("reason"))
            return {"status": log.status, "source": log.source, "schedule_date": ref.schedule_date.isoformat(), "item_count": log.item_count}

    return JobHandler(KIND, steps=(("fetch", fetch), ("store", store)))


def _store(db: Session, schedule: PbsSchedule, reason: str | None) -> PbsRefreshLog:
    """Sample data is always partial: it's a few drugs, not the schedule."""
    if schedule.source == "sample":
        status, detail = "partial", reason or "sample_loaded"
    elif schedule.skipped:
        status, detail = "partial", f"skipped_items:{schedule.skipped}"
    else:
        status, detail = "succeeded", None
    copayments = schedule.copayments
    log = PbsRefreshLog(
        schedule_date=schedule.schedule_date,
        refreshed_at=datetime.now(UTC),
        item_count=len(schedule.items),
        status=status,
        source=schedule.source,
        safety_net_general=copayments.safety_net_general,
        safety_net_concessional=copayments.safety_net_concessional,
        error_detail=detail,
    )
    db.add(log)
    db.flush()
    rows = [
        {
            "item_code": item.item_code,
            "drug_name": item.drug_name,
            "brand_names": list(item.brand_names),
            "form": item.form,
            "program_code": item.program_code,
            "restriction_level": item.restriction_level,
            "indications": [listing.as_json() for listing in item.listings],
            "max_quantity": item.max_quantity,
            "max_amount": item.max_amount,
            "amount_unit": item.amount_unit,
            "repeats": item.repeats,
            "patient_copay_general": copayments.general,
            "patient_copay_concessional": copayments.concessional,
            "schedule_date": schedule.schedule_date,
            "refresh_log_id": log.id,
            "raw_data": item.raw,
        }
        for item in schedule.items
    ]
    for batch in _batches(rows):
        statement = insert(PbsItem).values(batch)
        replaced = {column: statement.excluded[column] for column in batch[0] if column not in ("item_code", "schedule_date")}
        db.execute(statement.on_conflict_do_update(index_elements=["item_code", "schedule_date"], set_=replaced))
    return log


def _log_failure(db: Session, code: str, schedule_date: date | None = None) -> None:
    db.add(PbsRefreshLog(
        schedule_date=schedule_date, refreshed_at=datetime.now(UTC), status="failed", source="pbs_api", error_detail=code,
    ))


def _batches(rows: Sequence[dict[str, Any]]) -> Iterator[Sequence[dict[str, Any]]]:
    for start in range(0, len(rows), BATCH):
        yield rows[start:start + BATCH]
