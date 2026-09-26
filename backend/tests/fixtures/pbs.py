"""The PBS Schedule API, as tests see it: a recorded fixture (pbs_api.json), never the live service. It stands in
for the network under the real HTTP transport, so Refresh tests exercise its rate limiting and request log too."""

import io
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Any

import psycopg

from app.core.config import Settings
from app.core.database import session_factory
from app.core.seams.queue import JobStatus, NewJob
from app.db.provision import APP_ROLE, OWNER_ROLE, DatabaseSettings
from app.modules.pbs import refresh as pbs_refresh
from app.modules.pbs.api_client import HttpTransport, PbsApiClient
from app.modules.pbs.schedule import ScheduleSource
from app.core.jobs import JobHandler, JobRegistry
from app.orchestrator.queue import DbJobQueue
from app.orchestrator.worker import Worker
from tests.conftest import make_settings

RECORDING = Path(__file__).with_name("pbs_api.json")


class RecordedPbsApi:
    """Replays the recorded responses as `urlopen` would; a request that wasn't recorded fails the test. `down`
    paths are unreachable; `broken` paths answer with something the client can't read."""

    def __init__(self, down: Collection[str] = (), broken: Collection[str] = ()) -> None:
        self._responses = json.loads(RECORDING.read_text(encoding="utf-8"))["responses"]
        self.down = set(down)
        self.broken = set(broken)
        self.calls: list[str] = []

    def urlopen(self, request: urllib.request.Request, timeout: float) -> io.BytesIO:
        url = urllib.parse.urlsplit(request.full_url)
        path = url.path.removeprefix(urllib.parse.urlsplit(API_URL).path)
        self.calls.append(path)
        if path in self.down or "*" in self.down:
            raise urllib.error.URLError("unreachable")
        return io.BytesIO(json.dumps(self._body(path, dict(urllib.parse.parse_qsl(url.query)))).encode())

    def _body(self, path: str, params: Mapping[str, str]) -> Mapping[str, Any]:
        if path in self.broken:
            return {"data": [{"unexpected": "shape"}]}
        for response in self._responses:
            if response["path"] == path and {k: str(v) for k, v in response["params"].items()} == params:
                body: Mapping[str, Any] = response["body"]
                return body
        raise AssertionError(f"Not in the recorded PBS API fixture: {path} {params}")


API_URL = "http://pbs-api.invalid/pbs/api/v3"


def api(recorded: RecordedPbsApi) -> pbs_refresh.SourceFactory:
    """The real client and HTTP transport, with the recording for the network and no waiting between requests."""

    def source(settings: Settings) -> ScheduleSource:
        return PbsApiClient(HttpTransport(API_URL, "recorded-api-key", min_interval=0, urlopen=recorded.urlopen))

    return source


def clear_pbs(database: DatabaseSettings) -> None:
    """PBS data is shared by every Practice, so each PBS test starts from none (the owner may delete)."""
    with psycopg.connect(database.role_url(OWNER_ROLE), autocommit=True) as conn:
        conn.execute("DELETE FROM pbs_item")
        conn.execute("DELETE FROM pbs_refresh_log")


class PbsRefresher:
    """Runs PBS Refreshes through the worker, as Job Kind `kind` so other tests' queued Jobs aren't claimed."""

    def __init__(self, database: DatabaseSettings, kind: str, transport: RecordedPbsApi) -> None:
        registry = JobRegistry()
        registry.register(JobHandler(kind, steps=pbs_refresh.handler(api=api(transport)).steps))
        self.kind = kind
        self.queue = DbJobQueue(session_factory(database.role_url(APP_ROLE)))
        settings = make_settings(database_url=database.role_url(APP_ROLE))
        self.worker = Worker(self.queue, registry, settings, worker_id="test-pbs")

    def run(self) -> JobStatus:
        job_id = self.queue.enqueue(NewJob(kind=self.kind))
        self.worker.run_once()
        return self.queue.status(job_id)
