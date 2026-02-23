#!/usr/bin/env python3
"""Monitor upstream MCP references and emit a drift report."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
from urllib import error, parse, request


DEFAULT_TRACKING_PATH = Path("docs/interop/MCP_UPSTREAM_TRACKING.json")
DEFAULT_OUTPUT_PATH = Path("/tmp/mcp_watch_report.json")
DEFAULT_ISSUE_BODY_PATH = Path("/tmp/mcp_watch_issue.md")


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _github_get_json(url: str, token: str | None, timeout: int) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "faxp-mcp-watch/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(url=url, headers=headers, method="GET")
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def resolve_branch_head(repo: str, branch: str, token: str | None, timeout: int) -> dict:
    url = f"https://api.github.com/repos/{repo}/branches/{parse.quote(branch)}"
    payload = _github_get_json(url, token, timeout)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Invalid branch response for {repo}:{branch}")
    commit_sha = str(((payload.get("commit") or {}).get("sha") or "")).strip()
    return {
        "ref": branch,
        "refType": "branch",
        "url": str(payload.get("_links", {}).get("html") or f"https://github.com/{repo}/tree/{branch}"),
        "publishedAt": "",
        "commit": commit_sha,
    }


def resolve_latest_release_or_tag(repo: str, token: str | None, timeout: int) -> dict:
    base = f"https://api.github.com/repos/{repo}"

    release_url = f"{base}/releases/latest"
    try:
        payload = _github_get_json(release_url, token, timeout)
        if isinstance(payload, dict):
            tag = str(payload.get("tag_name") or "").strip()
            if tag:
                return {
                    "ref": tag,
                    "refType": "release",
                    "url": str(payload.get("html_url") or "").strip(),
                    "publishedAt": str(payload.get("published_at") or "").strip(),
                    "commit": "",
                }
    except error.HTTPError as exc:
        if exc.code not in {404}:
            raise

    tags_url = f"{base}/tags?{parse.urlencode({'per_page': 1})}"
    payload = _github_get_json(tags_url, token, timeout)
    if isinstance(payload, list) and payload:
        first = payload[0]
        tag = str((first or {}).get("name") or "").strip()
        commit_sha = str((((first or {}).get("commit") or {}).get("sha") or "")).strip()
        if tag:
            return {
                "ref": tag,
                "refType": "tag",
                "url": f"https://github.com/{repo}/tree/{tag}",
                "publishedAt": "",
                "commit": commit_sha,
            }

    raise RuntimeError(f"Unable to resolve latest release/tag for {repo}")


def resolve_latest_ref(repo: str, tracked_ref_type: str, tracked_ref: str, token: str | None, timeout: int) -> dict:
    if tracked_ref_type == "branch":
        return resolve_branch_head(repo, tracked_ref, token, timeout)
    return resolve_latest_release_or_tag(repo, token, timeout)


def build_issue_title(report: dict) -> str:
    if report.get("trackedRefType") == "branch" and report.get("trackedCommitMissing"):
        return f"[MCP Watch] Baseline commit missing for branch {report.get('trackedRef')}"
    tracked_ref = str(report.get("trackedRef") or "").strip() or "<unset>"
    latest_ref = str(report.get("latestRef") or "").strip() or "<unknown>"
    return f"[MCP Watch] Upstream drift detected: {tracked_ref} -> {latest_ref}"


def build_issue_body(report: dict) -> str:
    lines = [
        "## MCP Upstream Drift Detected",
        "",
        f"- CheckedAt: `{report['checkedAt']}`",
        f"- UpstreamRepo: `{report['upstreamRepo']}`",
        f"- TrackedRef: `{report['trackedRef']}` ({report['trackedRefType']})",
        f"- LatestRef: `{report['latestRef']}` ({report['latestRefType']})",
        f"- LatestURL: {report['latestUrl'] or 'N/A'}",
    ]
    if report.get("trackedRefType") == "branch":
        lines.extend(
            [
                f"- TrackedCommit: `{report.get('trackedCommit') or '<unset>'}`",
                f"- LatestCommit: `{report.get('latestCommit') or '<unknown>'}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Required Actions",
            "1. Review upstream MCP changes.",
            "2. Classify impact as `NoImpact`, `InteropUpdate`, or `CoreRisk`.",
            "3. If needed, update:",
            "   - `docs/interop/MCP_COMPATIBILITY_PROFILE.md`",
            "   - `conformance/mcp_tooling_contract.json`",
            "   - `tests/run_mcp_profile_check.py`",
            "4. Update `docs/interop/MCP_UPSTREAM_TRACKING.json` baseline after review.",
            "5. Open RFC before any FAXP core dependency change.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check upstream MCP drift.")
    parser.add_argument("--tracking", default=str(DEFAULT_TRACKING_PATH), help="Tracking JSON path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Report output JSON path")
    parser.add_argument(
        "--issue-body",
        default=str(DEFAULT_ISSUE_BODY_PATH),
        help="Issue body markdown output path",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=10,
        help="HTTP timeout for GitHub API requests",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when drift is detected.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tracking_path = Path(args.tracking).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    issue_body_path = Path(args.issue_body).expanduser().resolve()

    tracking = _load_json(tracking_path)
    upstream_repo = str(tracking.get("upstreamRepo") or "").strip()
    tracked_ref = str(tracking.get("trackedRef") or "").strip()
    tracked_ref_type = str(tracking.get("trackedRefType") or "unknown").strip().lower()
    tracked_commit = str(tracking.get("trackedCommit") or "").strip()

    if not upstream_repo or "/" not in upstream_repo:
        raise RuntimeError("tracking.upstreamRepo must be set as '<owner>/<repo>'.")
    if not tracked_ref:
        raise RuntimeError("tracking.trackedRef must be non-empty.")
    if tracked_ref_type not in {"release", "tag", "branch", "unknown"}:
        raise RuntimeError("tracking.trackedRefType must be release/tag/branch/unknown.")

    token = os.getenv("GITHUB_TOKEN", "").strip() or None
    latest = resolve_latest_ref(upstream_repo, tracked_ref_type, tracked_ref, token, args.timeout_seconds)

    latest_ref = str(latest.get("ref") or "").strip()
    latest_ref_type = str(latest.get("refType") or "unknown").strip()
    latest_url = str(latest.get("url") or "").strip()
    latest_commit = str(latest.get("commit") or "").strip()

    if not latest_ref:
        raise RuntimeError("Unable to resolve latest upstream ref.")

    tracked_commit_missing = tracked_ref_type == "branch" and tracked_commit == ""
    if tracked_ref_type == "branch":
        has_drift = tracked_commit_missing or (tracked_ref != latest_ref or tracked_commit != latest_commit)
    else:
        has_drift = latest_ref != tracked_ref

    report = {
        "checkedAt": now_utc(),
        "upstreamRepo": upstream_repo,
        "trackedRef": tracked_ref,
        "trackedRefType": tracked_ref_type,
        "trackedCommit": tracked_commit,
        "latestRef": latest_ref,
        "latestRefType": latest_ref_type,
        "latestCommit": latest_commit,
        "latestUrl": latest_url,
        "latestPublishedAt": str(latest.get("publishedAt") or "").strip(),
        "trackedCommitMissing": tracked_commit_missing,
        "hasDrift": has_drift,
    }
    report["issueTitle"] = build_issue_title(report)

    _write_json(output_path, report)
    issue_body_path.parent.mkdir(parents=True, exist_ok=True)
    issue_body_path.write_text(build_issue_body(report), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"[MCPWatch] report: {output_path}")
    print(f"[MCPWatch] issue body: {issue_body_path}")

    if args.strict and has_drift:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
