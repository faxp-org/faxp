#!/usr/bin/env python3
"""Generate or verify the developer-beta decision snapshot document."""

from __future__ import annotations

from pathlib import Path
import argparse
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CRITERIA_DOC_PATH = PROJECT_ROOT / "docs" / "governance" / "DEVELOPER_BETA_PROMOTION_CRITERIA.md"
SNAPSHOT_PATH = PROJECT_ROOT / "docs" / "releases" / "DEVELOPER_BETA_DECISION_SNAPSHOT.md"
CRITERIA_BEGIN = "<!-- DEVELOPER_BETA_PROMOTION_CRITERIA_BEGIN -->"
CRITERIA_END = "<!-- DEVELOPER_BETA_PROMOTION_CRITERIA_END -->"
SNAPSHOT_BEGIN = "<!-- DEVELOPER_BETA_DECISION_SNAPSHOT_BEGIN -->"
SNAPSHOT_END = "<!-- DEVELOPER_BETA_DECISION_SNAPSHOT_END -->"
ALLOWED_STATUSES = ("not_started", "in_progress", "blocked", "done")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _extract_block(document: str, begin: str, end: str) -> str:
    start = document.find(begin)
    stop = document.find(end)
    _assert(start != -1 and stop != -1 and stop > start, f"Missing or invalid block: {begin}")
    return document[start + len(begin) : stop].strip()


def _load_manifest(criteria_doc: Path) -> dict:
    _assert(criteria_doc.exists(), f"Missing criteria document: {criteria_doc}")
    payload = json.loads(_extract_block(criteria_doc.read_text(encoding="utf-8"), CRITERIA_BEGIN, CRITERIA_END))
    _assert(isinstance(payload, dict), "Criteria manifest must be a JSON object.")
    _assert("updatedAt" in payload, "Criteria manifest missing updatedAt.")
    _assert("betaDecision" in payload, "Criteria manifest missing betaDecision.")
    _assert("minimumIndependentImplementerDemos" in payload, "Criteria manifest missing minimumIndependentImplementerDemos.")
    criteria = payload.get("criteria") or []
    _assert(isinstance(criteria, list) and criteria, "Criteria manifest must include non-empty criteria array.")
    return payload


def _normalize_status(value: str) -> str:
    status = str(value or "").strip().lower()
    _assert(status in ALLOWED_STATUSES, f"Invalid criterion status: {status!r}")
    return status


def _decision_label(value: str) -> str:
    decision = str(value or "").strip().lower()
    _assert(decision in {"ready", "not_ready"}, f"Invalid beta decision value: {decision!r}")
    return "Ready" if decision == "ready" else "Not Ready"


def _format_status(status: str) -> str:
    return status.replace("_", " ").title()


def _build_snapshot_text(manifest: dict) -> str:
    criteria = manifest.get("criteria") or []

    counts = {status: 0 for status in ALLOWED_STATUSES}
    blockers = []
    for item in criteria:
        _assert(isinstance(item, dict), "Each criterion entry must be an object.")
        status = _normalize_status(str(item.get("status") or ""))
        counts[status] += 1
        if status != "done":
            blockers.append(item)

    decision = str(manifest["betaDecision"]).strip().lower()
    decision_label = _decision_label(decision)
    done = counts["done"]
    total = len(criteria)

    snapshot_payload = {
        "sourceCriteriaUpdatedAt": manifest["updatedAt"],
        "betaDecision": decision,
        "minimumIndependentImplementerDemos": int(manifest["minimumIndependentImplementerDemos"]),
        "counts": counts,
        "totalCriteria": total,
        "doneCriteria": done,
        "remainingCriteria": [
            {
                "id": str(item.get("id") or ""),
                "owner": str(item.get("owner") or ""),
                "due": str(item.get("due") or ""),
                "status": _normalize_status(str(item.get("status") or "")),
                "evidence": [str(ref) for ref in (item.get("evidence") or [])],
            }
            for item in blockers
        ],
    }

    lines: list[str] = []
    lines.append("# Developer Beta Decision Snapshot")
    lines.append("")
    lines.append("_Auto-generated from `docs/governance/DEVELOPER_BETA_PROMOTION_CRITERIA.md`._")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"- Source criteria updatedAt: `{manifest['updatedAt']}`")
    lines.append(f"- Decision: **{decision_label}**")
    lines.append(f"- Criteria completion: `{done}/{total}` done")
    lines.append(
        "- Minimum independent implementer demos required: "
        f"`{int(manifest['minimumIndependentImplementerDemos'])}`"
    )
    lines.append("")
    lines.append("## Criteria Status")
    lines.append("")
    lines.append(f"- Done: `{counts['done']}`")
    lines.append(f"- In Progress: `{counts['in_progress']}`")
    lines.append(f"- Blocked: `{counts['blocked']}`")
    lines.append(f"- Not Started: `{counts['not_started']}`")
    lines.append("")

    if blockers:
        lines.append("## Remaining Criteria")
        lines.append("")
        lines.append("| Criterion ID | Owner | Due | Status | Evidence |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in blockers:
            evidence = ", ".join(f"`{ref}`" for ref in (item.get("evidence") or []))
            lines.append(
                "| "
                f"`{str(item.get('id') or '').strip()}` | "
                f"{str(item.get('owner') or '').strip()} | "
                f"`{str(item.get('due') or '').strip()}` | "
                f"{_format_status(_normalize_status(str(item.get('status') or '')))} | "
                f"{evidence} |"
            )
        lines.append("")

    lines.append("## Machine Snapshot")
    lines.append("")
    lines.append(SNAPSHOT_BEGIN)
    lines.append(json.dumps(snapshot_payload, indent=2, sort_keys=True))
    lines.append(SNAPSHOT_END)
    lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate developer beta decision snapshot markdown.")
    parser.add_argument("--criteria-doc", default=str(CRITERIA_DOC_PATH), help="Path to criteria markdown doc.")
    parser.add_argument("--output", default=str(SNAPSHOT_PATH), help="Path to output snapshot markdown file.")
    parser.add_argument("--check", action="store_true", help="Fail if output is not up to date.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    criteria_doc = Path(args.criteria_doc).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    manifest = _load_manifest(criteria_doc)
    rendered = _build_snapshot_text(manifest)

    if args.check:
        _assert(output_path.exists(), f"Snapshot file missing: {output_path}")
        existing = output_path.read_text(encoding="utf-8")
        _assert(
            existing == rendered,
            "Developer beta decision snapshot is stale. Regenerate with scripts/generate_beta_decision_snapshot.py.",
        )
        print("Developer beta decision snapshot check passed.")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(f"Developer beta decision snapshot written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
