"""PBS Schedule API client (design doc §10.2): the Department of Health's public PBS API v3.

A fetch reads the whole schedule's program, item, ATC and restriction tables (one request per page) and keeps
every PBS Item. The public API allows one request every 20 seconds, so `HttpTransport` waits between requests
and a fetch takes a few minutes. The key (`VIGIL_PBS_API_KEY`) is never committed; without one, a fetch fails
with `pbs_api_key_missing`.
Tests give the client a recorded fixture (tests/fixtures/pbs_api.json) through `Transport`, never the service.
"""

import json
import logging
import math
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator, Mapping
from datetime import date
from decimal import Decimal
from html import unescape
from typing import Any

from app.modules.pbs.schedule import Copayments, Listing, Schedule, ScheduleItem, ScheduleRef, SourceUnreachable

log = logging.getLogger("vigil.pbs")

# A GET of `path` with query `params`, returning the decoded JSON body. Raises SourceUnreachable.
Transport = Callable[[str, Mapping[str, str | int]], Mapping[str, Any]]

PAGE_SIZE = 10000
ITEM_FIELDS = (
    "pbs_code", "drug_name", "schedule_form", "brand_name", "program_code", "benefit_type_code",
    "maximum_prescribable_pack", "maximum_quantity_units", "pack_size", "number_of_repeats", "maximum_amount",
    "unit_of_measure", "infusible_indicator",
)
RESTRICTION_FIELDS = ("res_code", "treatment_phase", "authority_method", "li_html_text")

# An item's benefit type, and a restriction's authority method, as a restriction level (models.RESTRICTION_LEVELS).
BENEFIT_TYPES = {
    "U": "unrestricted",
    "R": "restricted",
    "A": "authority_required",
    "S": "authority_required_streamlined",
}
AUTHORITY_METHODS = {
    "RESTRICTED": "restricted",
    "AUTHORITY_REQUIRED": "authority_required",
    "STREAMLINED": "authority_required_streamlined",
}


class HttpTransport:
    """GETs from the live API with the subscription key, at most one request per `min_interval` seconds. Logs each
    request (#31): its path, page, HTTP status, how long it took and how long it waited its turn; never the key
    or the rest of the query."""

    RATE_LIMIT_RETRIES = 3

    def __init__(
        self,
        base_url: str,
        subscription_key: str,
        min_interval: float = 20.0,
        timeout: float = 120.0,
        sleep: Callable[[float], None] = time.sleep,
        urlopen: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._key = subscription_key
        self._min_interval = min_interval
        self._timeout = timeout
        self._sleep = sleep
        self._urlopen = urlopen
        self._last: float | None = None

    def __call__(self, path: str, params: Mapping[str, str | int]) -> Mapping[str, Any]:
        if not self._key:
            raise SourceUnreachable("pbs_api_key_missing")
        url = f"{self._base_url}{path}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers={"Subscription-Key": self._key, "Accept": "application/json"})
        page = params.get("page", "-")
        for _ in range(self.RATE_LIMIT_RETRIES):
            waited = self._wait_turn()
            started = time.monotonic()
            status: int | str = "unreachable"
            try:
                with self._urlopen(request, timeout=self._timeout) as response:
                    status = 200
                    body: Mapping[str, Any] = json.load(response)
                return body
            except urllib.error.HTTPError as error:
                status = error.code
                if error.code == 429:
                    continue
                raise SourceUnreachable("pbs_api_refused" if error.code in (401, 403) else "pbs_api_unreachable") from None
            except (urllib.error.URLError, socket.timeout, ConnectionError):
                raise SourceUnreachable("pbs_api_unreachable") from None
            except ValueError:
                status = "bad_response"
                raise SourceUnreachable("pbs_api_bad_response") from None
            finally:
                retrying = " (rate limited: retrying)" if status == 429 else ""
                log.info(
                    "pbs api %s page=%s: %s in %.1fs, waited %.1fs%s",
                    path, page, status, time.monotonic() - started, waited, retrying,
                )
        raise SourceUnreachable("pbs_api_rate_limited")

    def _wait_turn(self) -> float:
        """Sleeps until this request's turn; returns how long."""
        now = time.monotonic()
        waited = 0.0
        if self._last is not None and now - self._last < self._min_interval:
            waited = self._min_interval - (now - self._last)
            self._sleep(waited)
        self._last = time.monotonic()
        return waited


class PbsApiClient:
    def __init__(self, transport: Transport, page_size: int = PAGE_SIZE) -> None:
        self._get = transport
        self._page_size = page_size

    def current(self) -> ScheduleRef:
        rows = self._data(self._get("/schedules", {"get_latest_schedule_only": "true"}))
        if not rows:
            raise SourceUnreachable("pbs_api_no_schedule")
        return ScheduleRef(schedule_code=int(rows[0]["schedule_code"]), schedule_date=date.fromisoformat(rows[0]["effective_date"]))

    def fetch(self, ref: ScheduleRef) -> Schedule:
        schedule = {"schedule_code": ref.schedule_code}
        copayments = self._copayments(self._data(self._get("/copayments", schedule)))
        programs = {row["program_code"]: row["program_title"] for row in self._all("/programs", schedule)}
        atc_codes: dict[str, set[str]] = {}
        for row in self._all("/item-atc-relationships", schedule):
            if row.get("atc_code"):
                atc_codes.setdefault(row["pbs_code"], set()).add(str(row["atc_code"]))
        rows_by_code: dict[str, list[Mapping[str, Any]]] = {}
        for row in self._all("/items", {**schedule, "fields": ",".join(ITEM_FIELDS)}):
            rows_by_code.setdefault(row["pbs_code"], []).append(row)
        links: dict[str, list[Mapping[str, Any]]] = {}
        for link in self._all("/item-restriction-relationships", schedule):
            # Restrictions only ("Y"); notes and cautions ("N") aren't indications.
            if link["pbs_code"] in rows_by_code and link.get("restriction_indicator") == "Y":
                links.setdefault(link["pbs_code"], []).append(link)
        wanted = {link["res_code"] for item_links in links.values() for link in item_links}
        restrictions = {
            row["res_code"]: row
            for row in self._all("/restrictions", {**schedule, "fields": ",".join(RESTRICTION_FIELDS)})
            if row["res_code"] in wanted
        }

        items, skipped = [], 0
        for code in sorted(rows_by_code):
            item = _item(rows_by_code[code], links.get(code, []), restrictions, atc_codes.get(code, set()), programs)
            if item is None:
                skipped += 1
            else:
                items.append(item)
        return Schedule(schedule_date=ref.schedule_date, copayments=copayments, items=tuple(items), skipped=skipped)

    def _all(self, path: str, params: Mapping[str, str | int]) -> Iterator[Mapping[str, Any]]:
        page, pages = 1, 1
        while page <= pages:
            body = self._get(path, {**params, "limit": self._page_size, "page": page})
            yield from self._data(body)
            total = int(body.get("_meta", {}).get("total_records") or 0)
            pages = math.ceil(total / self._page_size)
            page += 1

    @staticmethod
    def _data(body: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        data = body.get("data")
        if not isinstance(data, list):
            raise SourceUnreachable("pbs_api_bad_response")
        return data

    @staticmethod
    def _copayments(rows: list[Mapping[str, Any]]) -> Copayments:
        if not rows:
            raise SourceUnreachable("pbs_api_bad_response")
        row = rows[0]
        return Copayments(
            general=_decimal(row["general"]) or Decimal(0),
            concessional=_decimal(row["concessional"]) or Decimal(0),
            safety_net_general=_decimal(row.get("safety_net_general")),
            safety_net_concessional=_decimal(row.get("safety_net_concessional")),
        )


def _item(
    rows: list[Mapping[str, Any]],
    links: list[Mapping[str, Any]],
    restrictions: Mapping[str, Mapping[str, Any]],
    atc_codes: set[str],
    programs: Mapping[str, str],
) -> ScheduleItem | None:
    """One PBS item from its rows (one per brand). None if Vigil can't read its benefit type."""
    first = rows[0]
    level = BENEFIT_TYPES.get(str(first.get("benefit_type_code")))
    if level is None:
        return None
    listings = []
    for link in sorted(links, key=lambda link: link.get("res_position") or 0):
        restriction = restrictions.get(link["res_code"])
        if restriction is not None:
            listings.append(_listing(restriction, level))
    infusion = first.get("infusible_indicator") == "Y"
    return ScheduleItem(
        item_code=first["pbs_code"],
        drug_name=first["drug_name"],
        restriction_level=level,
        brand_names=tuple(sorted({row["brand_name"] for row in rows if row.get("brand_name")})),
        form=first.get("schedule_form"),
        program_code=first.get("program_code"),
        program_title=programs.get(first.get("program_code") or ""),
        atc_codes=tuple(sorted(atc_codes)),
        listings=tuple(listings),
        max_quantity=first.get("maximum_quantity_units"),
        max_packs=first.get("maximum_prescribable_pack"),
        pack_size=first.get("pack_size"),
        max_amount=_decimal(first.get("maximum_amount")) if infusion else None,
        amount_unit=first.get("unit_of_measure") if infusion else None,
        repeats=first.get("number_of_repeats"),
        raw=dict(first),
    )


PARAGRAPH = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL | re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")


def _listing(restriction: Mapping[str, Any], item_level: str) -> Listing:
    """A restriction's text is a heading, then the indication, the treatment phase (if any) and its prescribing
    conditions, as <p>s."""
    phase = restriction.get("treatment_phase")
    paragraphs = [" ".join(unescape(TAG.sub(" ", p)).split()) for p in PARAGRAPH.findall(restriction.get("li_html_text") or "")]
    paragraphs = [p for p in paragraphs if p]
    return Listing(
        indication=paragraphs[0] if paragraphs else "Indication not stated",
        level=AUTHORITY_METHODS.get(str(restriction.get("authority_method")), item_level),
        restriction_code=restriction["res_code"],
        treatment_phase=phase,
        conditions=tuple(p for p in paragraphs[1:] if p != phase),
    )


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))
