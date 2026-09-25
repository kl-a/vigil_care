import pytest

from gates import BACKEND, GATES, Gate, GateResult, run_gates


def passing() -> GateResult:
    return GateResult(passed=True, detail="all good")


def failing() -> GateResult:
    return GateResult(passed=False, detail="1 PII entity leaked")


def exploding() -> GateResult:
    raise RuntimeError("harness bug")


def test_refuses_to_run_outside_the_test_environment() -> None:
    with pytest.raises(SystemExit) as exit_info:
        run_gates([], environment="dev")
    assert exit_info.value.code == 2


def test_no_registered_gates_passes() -> None:
    assert run_gates([], environment="test") == 0


def test_all_passing_gates_pass() -> None:
    assert run_gates([Gate("pii", passing), Gate("leak", passing)], environment="test") == 0


def test_any_failing_gate_fails_the_build(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_gates([Gate("pii", passing), Gate("leak", failing)], environment="test") == 1
    assert "FAIL leak: 1 PII entity leaked" in capsys.readouterr().out


def test_a_gate_that_crashes_counts_as_a_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_gates([Gate("broken", exploding)], environment="test") == 1
    assert "FAIL broken" in capsys.readouterr().out


def test_the_no_patient_data_gate_runs_its_backend_test() -> None:
    assert [gate.name for gate in GATES] == ["No Patient data in support data"]
    assert (BACKEND / "tests/api/test_no_patient_data_in_support.py").is_file()
