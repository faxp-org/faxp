#!/usr/bin/env python3
"""Validate executable replay ops monitoring thresholds and SLO/budget evaluation."""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = PROJECT_ROOT / "scripts" / "evaluate_replay_ops.py"
PROFILE = PROJECT_ROOT / "docs" / "governance" / "REPLAY_OPS_MONITORING_PROFILE.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _evaluate(metrics: dict) -> dict:
    with tempfile.TemporaryDirectory(prefix="faxp-replay-ops-") as temp_dir:
        metrics_path = Path(temp_dir) / "metrics.json"
        metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(EVALUATOR),
                "--profile",
                str(PROFILE),
                "--metrics",
                str(metrics_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    return json.loads(completed.stdout.strip())


def _evaluate_with_state(metrics_sequence: list[dict]) -> list[dict]:
    outputs: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="faxp-replay-ops-state-") as temp_dir:
        state_path = Path(temp_dir) / "state.json"
        for metrics in metrics_sequence:
            metrics_path = Path(temp_dir) / "metrics.json"
            metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(EVALUATOR),
                    "--profile",
                    str(PROFILE),
                    "--metrics",
                    str(metrics_path),
                    "--state",
                    str(state_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            outputs.append(json.loads(completed.stdout.strip()))
    return outputs


def _evaluate_single_with_state(metrics: dict, state_path: Path) -> dict:
    metrics_path = state_path.parent / "metrics.json"
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(EVALUATOR),
            "--profile",
            str(PROFILE),
            "--metrics",
            str(metrics_path),
            "--state",
            str(state_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout.strip())


def main() -> int:
    _assert(EVALUATOR.exists(), "Missing replay ops evaluator script.")
    _assert(PROFILE.exists(), "Missing replay ops monitoring profile.")

    profile_payload = json.loads(PROFILE.read_text(encoding="utf-8"))
    _assert("slo" in profile_payload and "alerts" in profile_payload, "Profile missing required keys.")

    healthy = _evaluate(
        {
            "availability_percent": 100.0,
            "failure_rate_percent": 0.0,
            "reject_rate_percent": 0.0,
            "p95_latency_ms": 20,
            "p99_latency_ms": 40,
            "backend_unavailable_seconds": 0,
        }
    )
    _assert(healthy.get("status") == "ok", f"Expected healthy status=ok, got {healthy}")
    _assert(not healthy.get("alerts"), f"Expected no alerts for healthy metrics, got {healthy}")

    warn = _evaluate(
        {
            "availability_percent": 100.0,
            "failure_rate_percent": 0.0,
            "reject_rate_percent": 1.5,
            "p95_latency_ms": 70,
            "p99_latency_ms": 120,
            "backend_unavailable_seconds": 0,
        }
    )
    _assert(warn.get("status") == "warn", f"Expected warn status, got {warn}")
    alert_types = {(item.get("type"), item.get("severity")) for item in warn.get("alerts", [])}
    _assert(("reject_rate", "warn") in alert_types, "Expected reject_rate warn alert.")

    critical = _evaluate(
        {
            "availability_percent": 99.0,
            "failure_rate_percent": 3.0,
            "reject_rate_percent": 6.0,
            "p95_latency_ms": 100,
            "p99_latency_ms": 600,
            "backend_unavailable_seconds": 180,
        }
    )
    _assert(critical.get("status") == "critical", f"Expected critical status, got {critical}")
    _assert(
        "error_budget_breach" in critical.get("sloBreaches", []),
        f"Expected error budget breach in critical path, got {critical}",
    )
    critical_types = {(item.get("type"), item.get("severity")) for item in critical.get("alerts", [])}
    _assert(("reject_rate", "critical") in critical_types, "Expected reject_rate critical alert.")
    _assert(("failure_rate", "critical") in critical_types, "Expected failure_rate critical alert.")
    _assert(("latency_p99", "critical") in critical_types, "Expected p99 critical alert.")
    _assert(
        ("backend_unavailable", "critical") in critical_types,
        "Expected backend_unavailable critical alert.",
    )

    transition_outputs = _evaluate_with_state(
        [
            {
                "availability_percent": 99.0,
                "failure_rate_percent": 3.0,
                "reject_rate_percent": 6.0,
                "p95_latency_ms": 100,
                "p99_latency_ms": 600,
                "backend_unavailable_seconds": 180,
                "sample_window_minutes": 1,
            },
            {
                "availability_percent": 100.0,
                "failure_rate_percent": 0.0,
                "reject_rate_percent": 0.0,
                "p95_latency_ms": 20,
                "p99_latency_ms": 40,
                "backend_unavailable_seconds": 0,
                "sample_window_minutes": 1,
            },
        ]
    )
    first, second = transition_outputs
    _assert(first.get("status") == "critical", f"Expected initial critical status, got {first}")
    _assert(
        second.get("rawStatus") == "ok" and second.get("status") == "critical",
        f"Expected critical hold before clear window, got {second}",
    )
    _assert(second.get("clearPending") is True, "Expected clearPending=true during recovery hold.")

    stable_samples = [
        {
            "availability_percent": 100.0,
            "failure_rate_percent": 0.0,
            "reject_rate_percent": 0.0,
            "p95_latency_ms": 20,
            "p99_latency_ms": 40,
            "backend_unavailable_seconds": 0,
            "sample_window_minutes": 1,
        }
        for _ in range(16)
    ]
    settled = _evaluate_with_state(stable_samples)[-1]
    _assert(
        settled.get("status") == "ok" and settled.get("clearPending") is False,
        f"Expected clear after stable window, got {settled}",
    )

    bypass_probe = _evaluate_with_state(
        [
            {
                "availability_percent": 99.0,
                "failure_rate_percent": 3.0,
                "reject_rate_percent": 6.0,
                "p95_latency_ms": 100,
                "p99_latency_ms": 600,
                "backend_unavailable_seconds": 180,
                "sample_window_minutes": 1,
            },
            {
                "availability_percent": 100.0,
                "failure_rate_percent": 0.0,
                "reject_rate_percent": 0.0,
                "p95_latency_ms": 20,
                "p99_latency_ms": 40,
                "backend_unavailable_seconds": 0,
                "sample_window_minutes": 999,
            },
        ]
    )[-1]
    _assert(
        bypass_probe.get("status") == "critical" and bypass_probe.get("clearPending") is True,
        f"Expected hold for invalid sample_window_minutes, got {bypass_probe}",
    )
    bypass_alerts = {(item.get("type"), item.get("severity")) for item in bypass_probe.get("alerts", [])}
    _assert(
        ("invalid_sample_window", "critical") in bypass_alerts,
        f"Expected invalid sample window alert, got {bypass_probe}",
    )

    nan_window_probe = _evaluate_with_state(
        [
            {
                "availability_percent": 99.0,
                "failure_rate_percent": 3.0,
                "reject_rate_percent": 6.0,
                "p95_latency_ms": 100,
                "p99_latency_ms": 600,
                "backend_unavailable_seconds": 180,
                "sample_window_minutes": 1,
            },
            {
                "availability_percent": 100.0,
                "failure_rate_percent": 0.0,
                "reject_rate_percent": 0.0,
                "p95_latency_ms": 20,
                "p99_latency_ms": 40,
                "backend_unavailable_seconds": 0,
                "sample_window_minutes": "nan",
            },
        ]
    )[-1]
    _assert(
        nan_window_probe.get("status") == "critical" and nan_window_probe.get("clearPending") is True,
        f"Expected hold for non-finite sample_window_minutes, got {nan_window_probe}",
    )
    nan_window_alerts = {
        (item.get("type"), item.get("severity")) for item in nan_window_probe.get("alerts", [])
    }
    _assert(
        ("invalid_sample_window", "critical") in nan_window_alerts,
        f"Expected invalid sample window alert for NaN window, got {nan_window_probe}",
    )

    partial_metrics = _evaluate({"sample_window_minutes": 1})
    _assert(
        partial_metrics.get("status") == "critical",
        f"Expected critical status for partial metrics payload, got {partial_metrics}",
    )
    _assert(
        "metrics_missing_breach" in partial_metrics.get("sloBreaches", []),
        f"Expected metrics_missing_breach for partial payload, got {partial_metrics}",
    )
    validation = partial_metrics.get("inputValidation") or {}
    _assert(
        bool(validation.get("missingFields")),
        f"Expected missingFields in input validation output, got {partial_metrics}",
    )

    domain_extreme = _evaluate(
        {
            "availability_percent": 1e308,
            "failure_rate_percent": 0.0,
            "reject_rate_percent": 0.0,
            "p95_latency_ms": 20,
            "p99_latency_ms": 40,
            "backend_unavailable_seconds": 0,
        }
    )
    _assert(
        domain_extreme.get("status") == "critical",
        f"Expected critical status for out-of-domain availability, got {domain_extreme}",
    )
    _assert(
        "metrics_invalid_breach" in domain_extreme.get("sloBreaches", []),
        f"Expected metrics_invalid_breach for out-of-domain availability, got {domain_extreme}",
    )
    domain_validation = domain_extreme.get("inputValidation") or {}
    _assert(
        "availability_percent" in (domain_validation.get("invalidFields") or []),
        f"Expected availability_percent in invalidFields, got {domain_extreme}",
    )

    domain_negative = _evaluate(
        {
            "availability_percent": 100.0,
            "failure_rate_percent": -999.0,
            "reject_rate_percent": 0.0,
            "p95_latency_ms": 20,
            "p99_latency_ms": 40,
            "backend_unavailable_seconds": 0,
        }
    )
    _assert(
        domain_negative.get("status") == "critical",
        f"Expected critical status for negative failure rate, got {domain_negative}",
    )
    negative_validation = domain_negative.get("inputValidation") or {}
    _assert(
        "failure_rate_percent" in (negative_validation.get("invalidFields") or []),
        f"Expected failure_rate_percent in invalidFields, got {domain_negative}",
    )

    with tempfile.TemporaryDirectory(prefix="faxp-replay-ops-corrupt-state-") as temp_dir:
        state_path = Path(temp_dir) / "state.json"
        state_path.write_text("{not-json-state", encoding="utf-8")
        state_result = _evaluate_single_with_state(
            {
                "availability_percent": 100.0,
                "failure_rate_percent": 0.0,
                "reject_rate_percent": 0.0,
                "p95_latency_ms": 20,
                "p99_latency_ms": 40,
                "backend_unavailable_seconds": 0,
                "sample_window_minutes": 1,
            },
            state_path,
        )
        _assert(
            state_result.get("status") == "critical" and state_result.get("clearPending") is True,
            f"Expected fail-closed state handling for corrupt state file, got {state_result}",
        )
        state_alerts = {
            (item.get("type"), item.get("severity")) for item in state_result.get("alerts", [])
        }
        _assert(
            ("state_load_error", "critical") in state_alerts,
            f"Expected state_load_error alert for corrupt state file, got {state_result}",
        )

    with tempfile.TemporaryDirectory(prefix="faxp-replay-ops-state-shape-") as temp_dir:
        state_path = Path(temp_dir) / "state.json"
        state_path.write_text("[]", encoding="utf-8")
        state_result = _evaluate_single_with_state(
            {
                "availability_percent": 100.0,
                "failure_rate_percent": 0.0,
                "reject_rate_percent": 0.0,
                "p95_latency_ms": 20,
                "p99_latency_ms": 40,
                "backend_unavailable_seconds": 0,
                "sample_window_minutes": 1,
            },
            state_path,
        )
        _assert(
            state_result.get("status") == "critical" and state_result.get("clearPending") is True,
            f"Expected fail-closed state handling for non-object state payload, got {state_result}",
        )
        state_alerts = {
            (item.get("type"), item.get("severity")) for item in state_result.get("alerts", [])
        }
        _assert(
            ("state_load_error", "critical") in state_alerts,
            f"Expected state_load_error alert for non-object state payload, got {state_result}",
        )

    with tempfile.TemporaryDirectory(prefix="faxp-replay-ops-state-poison-") as temp_dir:
        state_path = Path(temp_dir) / "state.json"
        state_path.write_text(
            json.dumps(
                {
                    "effective_status": {"bad": "critical"},
                    "stable_minutes_below_warn": {"n": 999},
                }
            ),
            encoding="utf-8",
        )
        state_result = _evaluate_single_with_state(
            {
                "availability_percent": 100.0,
                "failure_rate_percent": 0.0,
                "reject_rate_percent": 0.0,
                "p95_latency_ms": 20,
                "p99_latency_ms": 40,
                "backend_unavailable_seconds": 0,
                "sample_window_minutes": 1,
            },
            state_path,
        )
        _assert(
            state_result.get("status") == "critical" and state_result.get("clearPending") is True,
            f"Expected fail-closed state handling for poisoned state payload, got {state_result}",
        )
        state_alerts = {
            (item.get("type"), item.get("severity")) for item in state_result.get("alerts", [])
        }
        _assert(
            ("state_load_error", "critical") in state_alerts,
            f"Expected state_load_error alert for poisoned state payload, got {state_result}",
        )

    print("Replay ops monitoring checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
