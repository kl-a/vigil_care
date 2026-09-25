"""Quality gates runner (docs/quality-gates.md).

Runs every registered gate against the Reference Set and exits non-zero if any
gate fails. Gates may only run in the test environment. Later phases register
their gates in GATES.
"""

import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class GateResult:
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class Gate:
    name: str
    run: Callable[[], GateResult]


GATES: list[Gate] = []


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
