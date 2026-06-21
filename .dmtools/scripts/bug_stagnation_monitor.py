#!/usr/bin/env python3
"""
Bug stagnation / deadlock detector for IstiN/trackstate.

Scans all open Bugs in the configured Jira project, detects:
  1. Stagnant bugs: status unchanged for a while and no active AI Teammate run.
  2. Deadlock cycles: a Bug is blocked by a Test Case that is Bug To Fix and
     that Test Case is linked back to the same Bug (or to another open Bug).

When a new issue is found, a comment is posted on the Bug and a short report
is printed to stdout. State is persisted so we do not spam the same ticket.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

JIRA_BASE = os.environ.get("JIRA_BASE_PATH", "https://dmtools.atlassian.net").rstrip("/")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_TOKEN = os.environ.get("JIRA_API_TOKEN")
PROJECT = os.environ.get("JIRA_PROJECT", "TS")
REPO = os.environ.get("TARGET_REPO", "IstiN/trackstate")

STAGNANT_HOURS = float(os.environ.get("BUG_STAGNANT_HOURS", "3"))
ALERT_COOLDOWN_HOURS = float(os.environ.get("BUG_ALERT_COOLDOWN_HOURS", "6"))
STATE_FILE = Path(os.environ.get("BUG_STAGNATION_STATE", "/Users/Uladzimir_Klyshevich/git/trackstate/.ai-bug-stagnation-state.json"))


@dataclass
class Finding:
    key: str
    status: str
    summary: str
    age_hours: float
    kind: str  # "stagnant" | "cycle"
    details: str


def jira_auth_header() -> dict[str, str]:
    if not JIRA_EMAIL or not JIRA_TOKEN:
        raise RuntimeError("JIRA_EMAIL and JIRA_API_TOKEN must be set")
    creds = f"{JIRA_EMAIL}:{JIRA_TOKEN}".encode()
    return {
        "Authorization": f"Basic {b64(creds)}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def b64(data: bytes) -> str:
    import base64
    return base64.b64encode(data).decode()


def jira_get(path: str) -> Any:
    url = f"{JIRA_BASE}{path}"
    req = urllib.request.Request(url, headers=jira_auth_header())
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def jira_search(jql: str, fields: list[str], max_results: int = 200) -> list[dict]:
    params = {
        "jql": jql,
        "fields": ",".join(fields),
        "maxResults": str(max_results),
    }
    url = f"{JIRA_BASE}/rest/api/3/search/jql?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=jira_auth_header())
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode()).get("issues", [])


def jira_post_comment(key: str, body: str) -> None:
    url = f"{JIRA_BASE}/rest/api/3/issue/{key}/comment"
    payload = json.dumps({"body": {"type": "doc", "version": 1, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": body}]}
    ]}}).encode()
    req = urllib.request.Request(url, data=payload, headers=jira_auth_header())
    with urllib.request.urlopen(req, timeout=60) as resp:
        resp.read()


def parse_jira_timestamp(ts: str) -> datetime:
    # Jira returns offsets like +0300; fromisoformat wants +03:00
    ts = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", ts)
    return datetime.fromisoformat(ts)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"alerts": {}}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


def should_alert(state: dict, key: str, kind: str) -> bool:
    last = state["alerts"].get(f"{key}:{kind}")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        return (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600 > ALERT_COOLDOWN_HOURS
    except Exception:
        return True


def record_alert(state: dict, key: str, kind: str) -> None:
    state["alerts"][f"{key}:{kind}"] = datetime.now(timezone.utc).isoformat()


def active_runs() -> list[dict]:
    try:
        result = subprocess.run(
            ["gh", "run", "list", "--repo", REPO, "--status", "in_progress", "--limit", "100", "--json", "databaseId,headBranch,displayTitle"],
            capture_output=True, text=True, timeout=60, check=False
        )
        if result.returncode != 0:
            print(f"Warning: gh run list failed: {result.stderr.strip()}", file=sys.stderr)
            return []
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Warning: could not fetch active runs: {e}", file=sys.stderr)
        return []


def is_active_for_bug(runs: list[dict], key: str) -> bool:
    for run in runs:
        text = f"{run.get('headBranch', '')} {run.get('displayTitle', '')}"
        if key in text or f"ai/{key}" in text:
            return True
    return False


def linked_test_cases(issue: dict) -> list[dict]:
    tcs = []
    for link in issue.get("fields", {}).get("issuelinks", []):
        other = link.get("outwardIssue") or link.get("inwardIssue")
        if not other:
            continue
        if other.get("fields", {}).get("issuetype", {}).get("name") == "Test Case":
            tcs.append(other)
    return tcs


def linked_bugs(tc_key: str) -> list[dict]:
    return jira_search(
        f'issue in linkedIssues("{tc_key}") AND issuetype = Bug',
        ["key", "status"],
    )


def find_stagnant_bugs(bugs: list[dict], runs: list[dict]) -> list[Finding]:
    now = datetime.now(timezone.utc)
    findings = []
    for bug in bugs:
        f = bug["fields"]
        updated = parse_jira_timestamp(f["updated"])
        age = (now - updated).total_seconds() / 3600
        if age < STAGNANT_HOURS:
            continue
        key = bug["key"]
        if is_active_for_bug(runs, key):
            continue
        findings.append(Finding(
            key=key,
            status=f["status"]["name"],
            summary=f["summary"],
            age_hours=age,
            kind="stagnant",
            details=f"status '{f['status']['name']}' unchanged for {age:.1f}h and no active AI Teammate run"
        ))
    return findings


def find_deadlock_cycles(bugs: list[dict]) -> list[Finding]:
    now = datetime.now(timezone.utc)
    findings = []
    for bug in bugs:
        key = bug["key"]
        status = bug["fields"]["status"]["name"]
        if status != "In Testing":
            continue
        tcs = linked_test_cases(bug)
        for tc in tcs:
            tc_status = tc["fields"]["status"]["name"]
            if tc_status not in ("Bug To Fix", "Failed", "Backlog", "In Development", "In Review - Passed", "In Review - Failed"):
                continue
            bugs_of_tc = linked_bugs(tc["key"])
            blocking_bugs = [b for b in bugs_of_tc if b["key"] != key and b["fields"]["status"]["name"] != "Done"]
            if not blocking_bugs:
                continue
            # Cycle / deadlock: the current bug is blocked by this TC, and the TC is
            # blocked by another open bug (possibly the current bug itself).
            cycle_keys = ", ".join(b["key"] for b in blocking_bugs)
            updated = parse_jira_timestamp(bug["fields"]["updated"])
            age = (now - updated).total_seconds() / 3600
            findings.append(Finding(
                key=key,
                status=status,
                summary=bug["fields"]["summary"],
                age_hours=age,
                kind="cycle",
                details=f"blocked by {tc['key']} ({tc_status}), which is blocked by open Bug(s): {cycle_keys}"
            ))
    return findings


def comment_for(finding: Finding) -> str:
    if finding.kind == "stagnant":
        return (
            f"h3. ⚠️ Automated Monitor Alert — Bug is stagnant\n\n"
            f"This Bug has been in status *{finding.status}* for *{finding.age_hours:.1f} hours* "
            f"and no active AI Teammate run was detected.\n\n"
            f"*Possible causes:*\n"
            f"- The relevant agent/workflow did not trigger.\n"
            f"- A Test Case or dependency is blocking progress.\n"
            f"- A cyclic dependency is preventing the status from advancing.\n\n"
            f"Please review the linked Test Cases and active workflows."
        )
    return (
        f"h3. 🔄 Automated Monitor Alert — Potential deadlock detected\n\n"
        f"This Bug is blocked by a Test Case that is itself blocked by another open Bug.\n\n"
        f"*Details:* {finding.details}\n\n"
        f"This pattern can create a cycle where neither ticket advances. "
        f"Consider unlinking unrelated regression Test Cases, marking infrastructure-only failures as Skipped/Irrelevant, "
        f"or fixing the blocking Bug first."
    )


def main() -> int:
    if not JIRA_EMAIL or not JIRA_TOKEN:
        print("JIRA_EMAIL and JIRA_API_TOKEN must be set", file=sys.stderr)
        return 1

    state = load_state()
    bugs = jira_search(
        f'project = {PROJECT} AND issuetype = Bug AND status NOT IN (Done, Canceled, Closed)',
        ["key", "summary", "status", "updated", "labels", "issuelinks"],
    )
    runs = active_runs()

    findings = []
    findings.extend(find_stagnant_bugs(bugs, runs))
    findings.extend(find_deadlock_cycles(bugs))

    new_alerts = 0
    for finding in findings:
        if not should_alert(state, finding.key, finding.kind):
            continue
        try:
            jira_post_comment(finding.key, comment_for(finding))
            record_alert(state, finding.key, finding.kind)
            new_alerts += 1
        except Exception as e:
            print(f"Failed to alert {finding.key}: {e}", file=sys.stderr)

    save_state(state)

    report = {
        "scanned_bugs": len(bugs),
        "active_runs": len(runs),
        "findings": [asdict(f) for f in findings],
        "new_alerts_posted": new_alerts,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
