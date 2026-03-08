#!/usr/bin/env python3
"""Evaluate replay operational metrics against policy thresholds."""

from __future__ import annotations

from pathlib import Path
import argparse
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_PATH = PROJECT_ROOT / "docs" / "governance" / "REPLAY_OPS_MONITORING_PROFILE.json"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _evaluate(profile: dict, metrics: dict) -> dict:
    alerts: list[dict[str, object]] = []
    breaches: list[str] = []

    slo = profile.get("slo") or {}
    alerts_cfg = profile.get("alerts") or {}

    availability_target = _to_float(slo.get("availability_target_percent"), 99.9)
    error_budget_percent = _to_float(slo.get("error_budget_percent"), 0.1)
    p95_target = _to_float((slo.get("latency_ms") or {}).get("p95_max"), 75)
    p99_target = _to_float((slo.get("latency_ms") or {}).get("p99_max"), 150)

    availability = _to_float(metrics.get("availability_percent"), 100.0)
    error_rate = _to_float(metrics.get("failure_rate_percent"), 0.0)
    reject_rate = _to_float(metrics.get("reject_rate_percent"), 0.0)
    p95_latency = _to_float(metrics.get("p95_latency_ms"), 0.0)
    p99_latency = _to_float(metrics.get("p99_latency_ms"), 0.0)
    backend_unavailable_seconds = _to_float(metrics.get("backend_unavailable_seconds"), 0.0)

    if availability < availability_target:
        breaches.append("availability_target_breach")
    if error_rate > error_budget_percent:
        breaches.append("error_budget_breach")
    if p95_latency > p95_target:
        breaches.append("p95_latency_slo_breach")
    if p99_latency > p99_target:
        breaches.append("p99_latency_slo_breach")

    reject_cfg = (alerts_cfg.get("reject_rate") or {})
    if reject_rate >= _to_float((reject_cfg.get("critical") or {}).get("threshold_percent"), 5.0):
        alerts.append({"type": "reject_rate", "severity": "critical", "value": reject_rate})
    elif reject_rate >= _to_float((reject_cfg.get("warn") or {}).get("threshold_percent"), 1.0):
        alerts.append({"type": "reject_rate", "severity": "warn", "value": reject_rate})

    failure_cfg = (alerts_cfg.get("failure_rate") or {})
    if error_rate >= _to_float((failure_cfg.get("critical") or {}).get("threshold_percent"), 2.0):
        alerts.append({"type": "failure_rate", "severity": "critical", "value": error_rate})

    latency_cfg = (alerts_cfg.get("latency") or {})
    if p99_latency >= _to_float((latency_cfg.get("critical_p99_ms") or {}).get("threshold_ms"), 500):
        alerts.append({"type": "latency_p99", "severity": "critical", "value": p99_latency})
    if p95_latency >= _to_float((latency_cfg.get("warn_p95_ms") or {}).get("threshold_ms"), 75):
        alerts.append({"type": "latency_p95", "severity": "warn", "value": p95_latency})

    backend_cfg = (alerts_cfg.get("backend_unavailable") or {})
    if backend_unavailable_seconds >= _to_float(
        (backend_cfg.get("critical") or {}).get("max_seconds"), 120
    ):
        alerts.append(
            {
                "type": "backend_unavailable",
                "severity": "critical",
                "value": backend_unavailable_seconds,
            }
        )

    status = "ok"
    if breaches or any(item.get("severity") == "critical" for item in alerts):
        status = "critical"
    elif alerts:
        status = "warn"

    return {
        "status": status,
        "alerts": alerts,
        "sloBreaches": breaches,
        "metrics": {
            "availability_percent": availability,
            "failure_rate_percent": error_rate,
            "reject_rate_percent": reject_rate,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": p99_latency,
            "backend_unavailable_seconds": backend_unavailable_seconds,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate replay ops metrics against policy.")
    parser.add_argument(
        "--profile",
        default=str(DEFAULT_PROFILE_PATH),
        help="Path to replay ops monitoring profile JSON.",
    )
    parser.add_argument(
        "--metrics",
        required=True,
        help="Path to replay ops metrics snapshot JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile = _load_json(Path(args.profile).expanduser().resolve())
    metrics = _load_json(Path(args.metrics).expanduser().resolve())
    _assert(isinstance(profile, dict), "Profile must be a JSON object.")
    _assert(isinstance(metrics, dict), "Metrics must be a JSON object.")
    result = _evaluate(profile, metrics)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
