"""The frontend's tests use the real shape of GET /modules/active with Oncology on. If Oncology's declared
sections or tabs change, this fails until frontend/tests/contracts/oncology-active.json is updated too, so the
frontend's renderers (frontend/modules/oncology/manifest.tsx) can't silently fall out of step."""

import json
from pathlib import Path

from app.modules.registry.builder import build
from app.modules.registry.service import as_api

CONTRACT = Path(__file__).resolve().parents[2] / "frontend" / "tests" / "contracts" / "oncology-active.json"


def test_the_frontend_contract_matches_the_builders_oncology_configuration() -> None:
    assert as_api(build(["oncology"])).model_dump() == json.loads(CONTRACT.read_text())
