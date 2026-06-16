#!/usr/bin/env python3
"""
Active AI Teammate run monitor.

Collects recently active/failed AI Teammate workflow runs for IstiN/trackstate,
downloads failure logs when available, extracts a concise error snippet, and
writes a JSON report for downstream investigation.

The monitor intentionally does NOT re-trigger or cancel any runs.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Union

REPO = "IstiN/trackstate"
WORKFLOW_NAME = "AI Teammate"
STATE_FILE = Path("/Users/Uladzimir_Klyshevich/git/trackstate/.ai-monitor-state.json")
REPORT_DIR = Path("/Users/Uladzimir_Klyshevich/git/trackstate/outputs/monitoring")
REPORT_FILE = REPORT_DIR / "active_run_report.json"

# How far back to look for failures (hours)
FAILURE_LOOKBACK_HOURS = 3
# Flag a still-in-progress run as stuck after this many minutes
STUCK_MINUTES = 45
# Flag a queued run as stale after this many minutes
STALE_QUEUED_MINUTES = 30


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_github_ts(ts: str) -> datetime:
    # GitHub timestamps are ISO 8601 with a Z suffix
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def fetch_recent_runs() -> List[dict]:
    """Return the most recent AI Teammate workflow runs via gh run list."""
    fields = [
        "databaseId",
        "number",
        "displayTitle",
        "status",
        "conclusion",
        "createdAt",
        "updatedAt",
        "headBranch",
        "name",
        "event",
        "url",
        "workflowName",
    ]
    cmd = [
        "gh", "run", "list",
        "--repo", REPO,
        "--workflow", WORKFLOW_NAME,
        "-L", "50",
        "--json", ",".join(fields),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"gh run list failed: {result.stderr.strip()}")
    runs = json.loads(result.stdout)
    # Normalize keys to match the rest of the script
    normalized = []
    for run in runs:
        normalized.append({
            "id": run.get("databaseId"),
            "run_number": run.get("number"),
            "display_title": run.get("displayTitle"),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "created_at": run.get("createdAt"),
            "updated_at": run.get("updatedAt"),
            "head_branch": run.get("headBranch"),
            "name": run.get("name"),
            "event": run.get("event"),
            "url": run.get("url"),
            "workflowName": run.get("workflowName"),
        })
    return normalized


def extract_ticket_key(run: dict) -> Optional[str]:
    """Best-effort ticket key extraction from run metadata."""
    # run_display_title is e.g. "agents/story_test_automation.json : TS-577 : TS-577"
    title = run.get("display_title") or run.get("name") or ""
    match = re.search(r"\b(TS-\d+)\b", title)
    if match:
        return match.group(1)
    head_branch = run.get("head_branch") or ""
    match = re.search(r"\b(TS-\d+)\b", head_branch)
    if match:
        return match.group(1)
    return None


def download_run_log(run_id: int) -> Optional[str]:
    """Download the log archive for a run and return the Run AI Teammate log text."""
    try:
        with tempfile.TemporaryDirectory(prefix=f"ai_run_{run_id}_") as tmpdir:
            zip_path = Path(tmpdir) / "logs.zip"
            url = f"repos/{REPO.replace('/', '/')}/actions/runs/{run_id}/logs"
            result = subprocess.run(
                ["gh", "api", url],
                capture_output=True,
                env={**os.environ, "GH_REPO": REPO},
            )
            if result.returncode != 0:
                return None
            zip_path.write_bytes(result.stdout)
            with zipfile.ZipFile(zip_path) as zf:
                candidates = [
                    name
                    for name in zf.namelist()
                    if name.endswith("Run AI Teammate.txt")
                ]
                if not candidates:
                    return None
                return zf.read(candidates[0]).decode("utf-8", errors="replace")
    except Exception as e:
        print(f"Could not download/extract logs for run {run_id}: {e}")
        return None


def extract_error_snippet(log_text: str) -> tuple[str, str]:
    """
    Extract a concise error snippet and category from the Run AI Teammate log.
    Returns (snippet, category).
    """
    lines = log_text.splitlines()

    # Look for explicit workflow error annotations
    for line in reversed(lines):
        if "::error::" in line:
            snippet = line.split("::error::", 1)[-1].strip()
            return snippet, "workflow_error_annotation"

    # Look for JavaScript action returning success:false
    for line in reversed(lines):
        if '"success":false' in line and "JavaScript executed successfully" in line:
            match = re.search(r'"success":false[^\n]*(?:"error":"([^"]+)")?', line)
            if match and match.group(1):
                return match.group(1), "js_action_success_false"
            return "JavaScript action returned success:false", "js_action_success_false"

    # Look for Java exception cause near the end
    for i, line in enumerate(reversed(lines)):
        if "Caused by:" in line:
            start = max(len(lines) - i - 5, 0)
            snippet = " | ".join(lines[start : len(lines) - i + 3])
            if "force-with-lease" in snippet or "stale info" in snippet:
                return "git push --force-with-lease failed with stale remote info", "stale_force_with_lease"
            if "Git operations failed" in snippet:
                return "Git operations failed during result publishing", "git_publish_failure"
            return snippet[:500], "java_exception"

    # Fallback: last non-empty lines
    tail = [ln for ln in lines[-20:] if ln.strip()]
    return " | ".join(tail[-5:])[:500], "unknown"


def build_report(runs: List[dict]) -> dict:
    cutoff = now_utc() - timedelta(hours=FAILURE_LOOKBACK_HOURS)
    entries = []

    for run in runs:
        run_id = run.get("id")
        status = run.get("status")
        conclusion = run.get("conclusion")
        created_at = parse_github_ts(run.get("created_at"))
        updated_at = parse_github_ts(run.get("updated_at"))
        ticket_key = extract_ticket_key(run)
        run_url = f"https://github.com/{REPO}/actions/runs/{run_id}"
        base_entry = {
            "runId": run_id,
            "runNumber": run.get("run_number"),
            "status": status,
            "conclusion": conclusion,
            "ticketKey": ticket_key,
            "runUrl": run_url,
            "createdAt": run.get("created_at"),
            "updatedAt": run.get("updated_at"),
            "branch": run.get("head_branch"),
            "displayTitle": run.get("display_title"),
        }

        if status == "in_progress":
            duration_min = (now_utc() - created_at).total_seconds() / 60
            if duration_min > STUCK_MINUTES:
                entry = dict(base_entry)
                entry["category"] = "stuck_active_run"
                entry["snippet"] = f"Run has been in_progress for {duration_min:.1f} minutes"
                entry["investigated"] = False
                entries.append(entry)
            continue

        if status == "queued":
            wait_min = (now_utc() - created_at).total_seconds() / 60
            if wait_min > STALE_QUEUED_MINUTES:
                entry = dict(base_entry)
                entry["category"] = "stale_queued_run"
                entry["snippet"] = f"Run has been queued for {wait_min:.1f} minutes"
                entry["investigated"] = False
                entries.append(entry)
            continue

        if status == "completed" and conclusion in ("failure", "startup_failure", "action_required"):
            if updated_at < cutoff:
                continue
            log_text = download_run_log(run_id)
            snippet, category = extract_error_snippet(log_text) if log_text else ("Could not retrieve run logs", "log_unavailable")
            entry = dict(base_entry)
            entry["category"] = category
            entry["snippet"] = snippet
            entry["investigated"] = False
            entries.append(entry)

    return {
        "generatedAt": now_utc().isoformat(),
        "repo": REPO,
        "total": len(entries),
        "entries": entries,
    }


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "monitorJobId": "ai-teammate-monitor-no-cancel",
        "count": 0,
        "maxCount": 100,
        "targetRepo": REPO,
        "targetWorkflow": WORKFLOW_NAME,
        "purpose": "Monitor active AI Teammate runs, read failures and stuck runs. Never re-trigger or cancel automatically.",
    }


def save_state(state: dict) -> None:
    state["count"] = state.get("count", 0) + 1
    state["lastRunAt"] = now_utc().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()

    try:
        runs = fetch_recent_runs()
        report = build_report(runs)
        REPORT_FILE.write_text(json.dumps(report, indent=2))
        print(f"Wrote active run report: {REPORT_FILE} ({report['total']} entries)")
        for entry in report["entries"]:
            print(f"  [{entry['category']}] run {entry['runNumber']} ({entry['ticketKey'] or 'no ticket'}): {entry['snippet'][:80]}")
    except Exception as e:
        print(f"Monitor failed: {e}")
        state["lastError"] = str(e)
        save_state(state)
        return 1

    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
