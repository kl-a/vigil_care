"""Quality gates runner (docs/quality-gates.md).

Runs every registered gate against the Reference Set and exits non-zero if any
gate fails. Gates may only run in the test environment. Later phases register
their gates in GATES.
"""

import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"


@dataclass(frozen=True)
class GateResult:
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class Gate:
    name: str
    run: Callable[[], GateResult]


def backend_test(path: str) -> Callable[[], GateResult]:
    """A gate that is a backend test file, run by pytest against a freshly migrated test database (its
    `database` fixture; the test Postgres must be up: `make test-db`)."""

    def run() -> GateResult:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", path],
            cwd=BACKEND,
            capture_output=True,
            text=True,
        )
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        failures = [line for line in lines if line.startswith("E ")]
        return GateResult(passed=result.returncode == 0, detail=" | ".join([*failures[:3], lines[-1] if lines else result.stderr.strip()]))

    return run


GATES: list[Gate] = [
    # Design doc §6.4: support data (support endpoints, application logs) never holds Patient data.
    Gate("No Patient data in support data", backend_test("tests/api/test_no_patient_data_in_support.py")),
]


def run_gates(gates: Sequence[Gate], environment: str) -> int:
    if environment != "test":
        print(f"Quality gates run only in the test environment (VIGIL_ENV={environment!r}).")
        raise SystemExit(2)
    if not gates:
        print("No quality gates registered yet.")
        return 0

    failures = 0
    for gate in gates:
        try:
            result = gate.run()
        except Exception as error:  # a crashing gate is a failing gate
            result = GateResult(passed=False, detail=f"gate crashed: {error!r}")
        status = "PASS" if result.passed else "FAIL"
        failures += 0 if result.passed else 1
        print(f"{status} {gate.name}: {result.detail}")
    print(f"{len(gates) - failures}/{len(gates)} gates passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run_gates(GATES, os.environ.get("VIGIL_ENV", "")))
