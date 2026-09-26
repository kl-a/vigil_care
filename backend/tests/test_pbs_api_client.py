"""The PBS Schedule API's HTTP transport (#31): each request is logged with its path, page, status and timings,
so a slow Refresh shows why (the API allows one request every 20 seconds, and may answer 429). Never the network:
`urlopen` is replaced.
"""

import io
import json
import logging
import urllib.error
import urllib.request
from email.message import Message
from typing import Any

import pytest

from app.modules.pbs.api_client import HttpTransport
from app.modules.pbs.schedule import SourceUnreachable


class FakeApi:
    """Answers each request with the next status: 429 is "too many requests", 200 a small JSON body, 0 no answer,
    1 a body that isn't JSON."""

    def __init__(self, *statuses: int) -> None:
        self._statuses = list(statuses)
        self.urls: list[str] = []

    def __call__(self, request: urllib.request.Request, timeout: float) -> Any:
        self.urls.append(request.full_url)
        status = self._statuses.pop(0)
        if status == 0:
            raise urllib.error.URLError("connection refused")
        if status == 1:
            return io.BytesIO(b"<html>not json</html>")
        if status != 200:
            raise urllib.error.HTTPError(request.full_url, status, "refused", Message(), None)
        return io.BytesIO(json.dumps({"data": []}).encode())


def transport(api: FakeApi, slept: list[float]) -> HttpTransport:
    return HttpTransport("https://pbs.example/api", "test-key", min_interval=20.0, sleep=slept.append, urlopen=api)


def test_each_request_is_logged_with_its_path_page_status_and_timings(caplog: pytest.LogCaptureFixture) -> None:
    slept: list[float] = []
    get = transport(FakeApi(200, 200), slept)
    with caplog.at_level(logging.INFO, logger="vigil.pbs"):
        assert get("/items", {"schedule_code": 4333, "page": 2}) == {"data": []}
        get("/restrictions", {"schedule_code": 4333, "page": 1})
    lines = [record.getMessage() for record in caplog.records if record.name == "vigil.pbs"]
    assert len(lines) == 2
    assert lines[0].startswith("pbs api /items page=2: 200 in ")
    assert lines[1].startswith("pbs api /restrictions page=1: 200 in ")
    assert "waited 0.0s" in lines[0]
    assert len(slept) == 1 and 19 < slept[0] <= 20  # one request every 20 seconds
    assert f"waited {slept[0]:.1f}s" in lines[1]


def test_a_rate_limited_request_is_retried_and_logged_as_such(caplog: pytest.LogCaptureFixture) -> None:
    slept: list[float] = []
    api = FakeApi(429, 200)
    with caplog.at_level(logging.INFO, logger="vigil.pbs"):
        assert transport(api, slept)("/items", {"page": 1}) == {"data": []}
    lines = [record.getMessage() for record in caplog.records if record.name == "vigil.pbs"]
    assert [line.split(" in ")[0] for line in lines] == ["pbs api /items page=1: 429", "pbs api /items page=1: 200"]
    assert lines[0].endswith("(rate limited: retrying)") and "retrying" not in lines[1]
    assert len(api.urls) == 2 and len(slept) == 1  # the retry waited its turn


def test_the_log_never_holds_the_key_or_the_full_query(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="vigil.pbs"):
        transport(FakeApi(200), [])("/items", {"schedule_code": 4333, "fields": "pbs_code,drug_name", "page": 1})
    logged = " ".join(record.getMessage() for record in caplog.records)
    assert "test-key" not in logged and "drug_name" not in logged


def test_an_unreachable_api_is_logged_before_the_refresh_hears_of_it(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="vigil.pbs"), pytest.raises(SourceUnreachable):
        transport(FakeApi(0), [])("/items", {"page": 1})
    assert [record.getMessage().split(" in ")[0] for record in caplog.records] == ["pbs api /items page=1: unreachable"]


def test_an_answer_that_isnt_json_is_logged_too(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="vigil.pbs"), pytest.raises(SourceUnreachable) as refused:
        transport(FakeApi(1), [])("/items", {"page": 1})
    assert refused.value.code == "pbs_api_bad_response"
    assert [record.getMessage().split(" in ")[0] for record in caplog.records] == ["pbs api /items page=1: bad_response"]
