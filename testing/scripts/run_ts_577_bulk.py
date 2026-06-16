from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = REPO_ROOT / "input" / "TS-577" / "linked_test_cases.json"
OUTPUTS_DIR = REPO_ROOT / "outputs"
TESTS_DIR = REPO_ROOT / "testing" / "tests"

# Test cases that are linked but cannot be executed in this environment because they
# require write access, a fork, a live release, a Windows/macOS host, or Playwright.
ENVIRONMENT_SKIP = {
    "TS-252",  # push/merge to non-default branch in IstiN/trackstate-setup
    "TS-251",  # push invalid workflow to trigger actionlint
    "TS-250",  # create disposable PR for dry-run check
    "TS-230",  # merge PR to main and observe release/tag
    "TS-256",  # push valid workflow change
    "TS-1319",  # create semantic tag and wait for Apple workflow
    "TS-709",  # Playwright + live run history
    "TS-708",  # download published macOS release artifacts
    "TS-707",  # mutate workflow and create tag
    "TS-69",  # fork trackstate-setup and run workflow
    "TS-74",  # CLI quick start against a fork
}


def discover_test_file(tc_key: str) -> Path | None:
    folder = TESTS_DIR / tc_key
    if not folder.is_dir():
        return None
    numeric = tc_key.split("-", 1)[1]
    candidates = [
        folder / f"test_ts_{numeric}.py",
        folder / f"test_ts_{tc_key.lower()}.py",
        folder / f"test_{tc_key.lower()}.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    # Fallback: any test_*.py in the folder
    for candidate in folder.glob("test_*.py"):
        return candidate
    return None


def run_test(tc_key: str, test_file: Path) -> dict[str, object]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    try:
        result = subprocess.run(
            [sys.executable, str(test_file)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=env,
            timeout=600,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": -1,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
        }
    except Exception as exc:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
            "timed_out": False,
        }

    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "timed_out": False,
    }


def build_result(tc: dict[str, object]) -> dict[str, object]:
    tc_key = tc["key"]
    tracker_status = tc["fields"]["status"]["name"]
    if tracker_status == "Irrelevant":
        return {
            "testCaseKey": tc_key,
            "status": "irrelevant",
            "summary": "Marked irrelevant in the linked test case list.",
        }

    if tc_key in ENVIRONMENT_SKIP:
        return {
            "testCaseKey": tc_key,
            "status": "skipped",
            "summary": "Skipped: requires write/admin access, a fork, a live release tag, or a platform/browser not available in this environment.",
        }

    test_file = discover_test_file(tc_key)
    if test_file is None:
        return {
            "testCaseKey": tc_key,
            "status": "failed",
            "failureSummary": "No automated test file found in testing/tests/{tc_key}/.",
            "testPath": None,
            "failedDescriptionFile": f"outputs/failed_description_{tc_key}.md",
        }

    run = run_test(tc_key, test_file)
    rel_path = test_file.relative_to(REPO_ROOT)

    if run["exit_code"] == 0:
        return {
            "testCaseKey": tc_key,
            "status": "passed",
            "testPath": str(rel_path),
            "summary": "Test executed successfully.",
        }

    combined = (run.get("stdout") or "") + "\n" + (run.get("stderr") or "")
    if run.get("timed_out"):
        failure_summary = "Test timed out after 600 seconds."
    else:
        failure_summary = "Test exited with a non-zero status."
    # Try to surface a more specific one-line failure summary from the test output.
    for line in reversed(combined.splitlines()):
        stripped = line.strip()
        if stripped.startswith("FAIL:") or stripped.startswith("AssertionError:"):
            failure_summary = stripped[:200]
            break

    return {
        "testCaseKey": tc_key,
        "status": "failed",
        "testPath": str(rel_path),
        "failedDescriptionFile": f"outputs/failed_description_{tc_key}.md",
        "failureSummary": failure_summary,
        "stdout": run.get("stdout") or "",
        "stderr": run.get("stderr") or "",
        "combined_output": combined.strip(),
    }


def write_failed_description(tc: dict[str, object], result: dict[str, object]) -> None:
    tc_key = result["testCaseKey"]
    summary = tc["fields"]["summary"]
    description = tc["fields"].get("description", "")
    path = OUTPUTS_DIR / f"failed_description_{tc_key}.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"h1. {tc_key} — {summary}",
        "",
        "h2. Steps to Reproduce",
        description.strip() or "See linked test case description.",
        "",
        "h2. Expected Result",
        "The automated test should pass.",
        "",
        "h2. Actual Result",
        result["failureSummary"],
        "",
        "h2. Logs / Output",
        "{code:text}",
        result.get("combined_output", ""),
        "{code}",
        "",
        "h2. Environment",
        f"* Repository: {os.environ.get('GITHUB_REPOSITORY', 'IstiN/trackstate')}",
        f"* Branch: {os.environ.get('GITHUB_REF_NAME', 'unknown')}",
        f"* Test file: {result.get('testPath', 'N/A')}",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(results: list[dict[str, object]]) -> None:
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] in ("skipped", "irrelevant"))

    if failed > 0:
        overall = "failed"
    else:
        overall = "passed"

    story_result = {
        "storyKey": "TS-577",
        "overall": overall,
        "summary": f"TS-577 bulk run: {passed} passed, {failed} failed, {skipped} skipped/irrelevant.",
        "results": [
            {
                "testCaseKey": r["testCaseKey"],
                "status": r["status"],
                "testPath": (
                    r.get("testPath")
                    if r["status"] in ("passed", "failed")
                    else None
                ),
                "failedDescriptionFile": r.get("failedDescriptionFile"),
                "failureSummary": r.get("failureSummary"),
            }
            for r in results
        ],
    }

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "story_test_automation_result.json").write_text(
        json.dumps(story_result, indent=2) + "\n", encoding="utf-8"
    )

    comment_lines = [
        "h1. TS-577 — Publish TrackState CLI binaries for Linux, macOS, and Windows",
        "",
        f"*Overall:* {'✅ PASSED' if overall == 'passed' else '❌ FAILED'}",
        f"*Summary:* {story_result['summary']}",
        "",
        "h2. Results by Test Case",
        "",
        f"* Passed: {passed}",
        f"* Failed: {failed}",
        f"* Skipped / Irrelevant: {skipped}",
        "",
    ]

    if failed:
        comment_lines.extend(["h2. Failed Test Cases", ""])
        for r in results:
            if r["status"] == "failed":
                desc_file = r.get("failedDescriptionFile")
                link = f"[{desc_file}|{desc_file}]" if desc_file else "N/A"
                comment_lines.append(
                    f"* *{r['testCaseKey']}* — {r.get('failureSummary', 'failed')} ({link})"
                )
        comment_lines.append("")

    skipped_items = [r for r in results if r["status"] in ("skipped", "irrelevant")]
    if skipped_items:
        comment_lines.extend(["h2. Skipped / Irrelevant Test Cases", ""])
        for r in skipped_items:
            comment_lines.append(f"* *{r['testCaseKey']}* — {r.get('summary', '')}")
        comment_lines.append("")

    comment_lines.extend([
        "h2. How to Re-run",
        "{code:bash}",
        "python testing/scripts/run_ts_577_bulk.py",
        "{code}",
        "",
    ])

    (OUTPUTS_DIR / "tracker_comment.md").write_text(
        "\n".join(comment_lines) + "\n", encoding="utf-8"
    )


def main() -> int:
    if not INPUT_PATH.exists():
        print(f"Input file not found: {INPUT_PATH}", file=sys.stderr)
        return 1

    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    test_cases = payload["testCases"]

    results: list[dict[str, object]] = []
    for tc in test_cases:
        result = build_result(tc)
        results.append(result)
        if result["status"] == "failed":
            write_failed_description(tc, result)

    write_outputs(results)

    failed_count = sum(1 for r in results if r["status"] == "failed")
    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
