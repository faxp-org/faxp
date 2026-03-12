#!/usr/bin/env python3
"""Export GitHub policy/security settings snapshots for drift review."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
import urllib.error
import urllib.request


API_BASE = "https://api.github.com"
DEFAULT_REPO = "faxp-org/faxp"


@dataclass(frozen=True)
class Endpoint:
    name: str
    path: str
    auth_required: bool = False


ENDPOINTS = (
    Endpoint("repo", "/repos/{repo}"),
    Endpoint("rulesets", "/repos/{repo}/rulesets"),
    Endpoint("actions_permissions", "/repos/{repo}/actions/permissions", auth_required=True),
    Endpoint(
        "actions_workflow_permissions",
        "/repos/{repo}/actions/permissions/workflow",
        auth_required=True,
    ),
    Endpoint(
        "actions_selected_actions",
        "/repos/{repo}/actions/permissions/selected-actions",
        auth_required=True,
    ),
    Endpoint(
        "actions_fork_pr_approval",
        "/repos/{repo}/actions/permissions/fork-pr-contributor-approval",
        auth_required=True,
    ),
    Endpoint("branch_protection_main", "/repos/{repo}/branches/main/protection", auth_required=True),
    Endpoint("dependabot_alerts_sample", "/repos/{repo}/dependabot/alerts?per_page=1", auth_required=True),
    Endpoint(
        "code_scanning_alerts_sample",
        "/repos/{repo}/code-scanning/alerts?per_page=1",
        auth_required=True,
    ),
    Endpoint(
        "secret_scanning_alerts_sample",
        "/repos/{repo}/secret-scanning/alerts?per_page=1",
        auth_required=True,
    ),
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export GitHub policy snapshot JSON.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository in owner/name format.")
    parser.add_argument(
        "--output-dir",
        default="artifacts/policy-snapshot",
        help="Output directory for JSON snapshot files.",
    )
    parser.add_argument(
        "--token-env",
        default="POLICY_SNAPSHOT_TOKEN",
        help="Environment variable that contains the GitHub token.",
    )
    return parser.parse_args()


def _request_json(url: str, token: str) -> tuple[int, object]:
    request = urllib.request.Request(url, method="GET")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = int(response.status)
            payload = json.loads(response.read().decode("utf-8"))
            return status, payload
    except urllib.error.HTTPError as exc:
        payload = {"message": exc.reason}
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            pass
        return int(exc.code), payload


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = _parse_args()
    token = os.getenv(args.token_env, "").strip()
    if not token:
        raise SystemExit(f"Missing token in environment variable {args.token_env}.")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = Path(args.output_dir).expanduser().resolve() / ts
    root.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {
        "generatedAtUtc": ts,
        "repo": args.repo,
        "endpoints": [],
        "authGatedFailures": [],
    }

    for endpoint in ENDPOINTS:
        path = endpoint.path.format(repo=args.repo)
        url = f"{API_BASE}{path}"
        status, payload = _request_json(url, token)
        _write_json(
            root / f"{endpoint.name}.json",
            {"status": status, "path": path, "payload": payload},
        )
        record = {"name": endpoint.name, "path": path, "status": status}
        summary["endpoints"].append(record)
        if endpoint.auth_required and status >= 400:
            summary["authGatedFailures"].append(record)

    # Expand ruleset detail snapshots when available.
    rulesets_payload_path = root / "rulesets.json"
    rulesets_payload = json.loads(rulesets_payload_path.read_text(encoding="utf-8"))
    if rulesets_payload.get("status") == 200 and isinstance(rulesets_payload.get("payload"), list):
        details_dir = root / "rulesets"
        details_dir.mkdir(parents=True, exist_ok=True)
        for item in rulesets_payload["payload"]:
            ruleset_id = item.get("id")
            if ruleset_id is None:
                continue
            ruleset_path = f"/repos/{args.repo}/rulesets/{ruleset_id}"
            status, payload = _request_json(f"{API_BASE}{ruleset_path}", token)
            _write_json(
                details_dir / f"{ruleset_id}.json",
                {"status": status, "path": ruleset_path, "payload": payload},
            )

    _write_json(root / "summary.json", summary)
    print(f"Policy snapshot written to {root}")

    if summary["authGatedFailures"]:
        print("Auth-gated endpoint failures detected:")
        for item in summary["authGatedFailures"]:
            print(f" - {item['name']} [{item['status']}]")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
