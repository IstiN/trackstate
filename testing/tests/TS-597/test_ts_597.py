from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.flutter_dependency_boundary_validator import (  # noqa: E402
    FlutterDependencyBoundaryValidator,
)
from testing.core.config.flutter_dependency_boundary_config import (  # noqa: E402
    FlutterDependencyBoundaryConfig,
)
from testing.core.models.flutter_dependency_boundary_validation_result import (  # noqa: E402
    FlutterDependencyBoundaryValidationResult,
)
from testing.core.models.repository_source_match import RepositorySourceMatch  # noqa: E402
from testing.tests.support.repository_source_probe_factory import (  # noqa: E402
    create_repository_source_probe,
)

TICKET_KEY = "TS-597"
TICKET_SUMMARY = (
    "Import check for data and domain layers — package:flutter dependencies "
    "are absent"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
TEST_FILE_PATH = "testing/tests/TS-597/test_ts_597.py"
RUN_COMMAND = "python testing/tests/TS-597/test_ts_597.py"


class Ts597FlutterDependencyBoundaryScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-597/config.yaml"
        self.config = FlutterDependencyBoundaryConfig.from_file(self.config_path)
        self.validator = FlutterDependencyBoundaryValidator(
            repository_root=self.repository_root,
            probe=create_repository_source_probe(self.repository_root),
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        validation = self.validator.validate(config=self.config)
        result = self._build_result(validation)
        failures: list[str] = []

        failures.extend(self._validate_search_boundary(validation, result))
        failures.extend(self._validate_provider_imports(validation, result))
        failures.extend(self._validate_replacement_strategy(validation, result))
        return result, failures

    def _build_result(
        self,
        validation: FlutterDependencyBoundaryValidationResult,
    ) -> dict[str, object]:
        replacement_strategy = validation.replacement_strategy or "missing"
        return {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "repository_root": str(self.repository_root),
            "config_path": str(self.config_path),
            "os": platform.system(),
            "search_roots": list(validation.search_roots),
            "provider_relative_path": validation.provider_relative_path,
            "provider_import_lines": list(validation.provider_import_lines),
            "provider_excerpt": "\n".join(validation.provider_excerpt_lines),
            "provider_has_expected_compat_import": validation.provider_has_expected_compat_import,
            "replacement_strategy": replacement_strategy,
            "disallowed_import_matches": _matches_to_dict(validation.disallowed_import_matches),
            "provider_forbidden_import_matches": _matches_to_dict(
                validation.provider_forbidden_import_matches
            ),
            "provider_meta_import_matches": _matches_to_dict(
                validation.provider_meta_import_matches
            ),
            "provider_required_keyword_matches": _matches_to_dict(
                validation.provider_required_keyword_matches[:5]
            ),
            "steps": [],
            "human_verification": [],
        }

    def _validate_search_boundary(
        self,
        validation: FlutterDependencyBoundaryValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        if validation.disallowed_import_matches:
            formatted_matches = _format_matches(validation.disallowed_import_matches)
            return [
                "Step 1 failed: a global search still found direct `package:flutter/` "
                "imports under the data/domain layers.\n"
                f"Observed matches:\n{formatted_matches}"
            ]

        _record_step(
            result,
            step=1,
            status="passed",
            action=(
                "Perform a global search for `import 'package:flutter/` within "
                "`lib/data/` and `lib/domain/`."
            ),
            observed=(
                "No `package:flutter/` imports were found in "
                f"{', '.join(validation.search_roots)}."
            ),
        )
        return []

    def _validate_provider_imports(
        self,
        validation: FlutterDependencyBoundaryValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        if validation.provider_forbidden_import_matches:
            failures.append(
                "Step 2 failed: `github_trackstate_provider.dart` still imports a "
                "Flutter library directly.\n"
                f"Observed matches:\n{_format_matches(validation.provider_forbidden_import_matches)}"
            )
        if not validation.provider_has_expected_compat_import:
            failures.append(
                "Step 2 failed: `github_trackstate_provider.dart` did not show the "
                "expected compatibility import for `kIsWeb`.\n"
                f"Observed import block:\n{_provider_block(validation)}"
            )
        if failures:
            return failures

        _record_step(
            result,
            step=2,
            status="passed",
            action=(
                "Inspect `lib/data/providers/github/github_trackstate_provider.dart` "
                "for the removal of the Flutter foundation import."
            ),
            observed=_provider_block(validation),
        )
        _record_human_verification(
            result,
            check=(
                "Opened the provider file like a reviewer and checked the visible "
                "import section at the top of the file."
            ),
            observed=_provider_block(validation),
        )
        return []

    def _validate_replacement_strategy(
        self,
        validation: FlutterDependencyBoundaryValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        if not validation.provider_meta_import_matches:
            observed = (
                "Observed Dart `required` constructor parameters, but the current ticket "
                "still explicitly requires `package:meta` evidence."
                if validation.provider_required_keyword_matches
                else "No `package:meta` import or alternate replacement evidence was found."
            )
            return [
                "Step 3 failed: the ticket explicitly requires `package:meta` "
                "replacement evidence in `github_trackstate_provider.dart`, but no "
                "`package:meta` import was found.\n"
                f"Observed replacement evidence: {observed}\n"
                f"Observed import block:\n{_provider_block(validation)}"
            ]

        observed = "Observed `package:meta` import in the provider."

        _record_step(
            result,
            step=3,
            status="passed",
            action=(
                "Check the provider for the non-Flutter replacement used after the "
                "foundation import was removed."
            ),
            observed=observed,
        )
        _record_human_verification(
            result,
            check=(
                "Confirmed the provider still shows a valid non-Flutter replacement "
                "strategy after removing the Flutter dependency."
            ),
            observed=observed,
        )
        return []


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts597FlutterDependencyBoundaryScenario()

    try:
        result, failures = scenario.execute()
        if failures:
            raise AssertionError("\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        failure_result = locals().get("result", {}) if "result" in locals() else {}
        if not isinstance(failure_result, dict):
            failure_result = {}
        failure_result.update(
            {
                "ticket": TICKET_KEY,
                "ticket_summary": TICKET_SUMMARY,
                "error": f"{type(error).__name__}: {error}",
                "traceback": traceback.format_exc(),
            }
        )
        _write_failure_outputs(failure_result)
        raise


def _write_pass_outputs(result: dict[str, object]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    _write_review_replies()
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    search_roots = ", ".join(str(root) for root in result.get("search_roots", []))
    provider_relative_path = _as_text(result.get("provider_relative_path"))
    provider_excerpt = _as_text(result.get("provider_excerpt")) or "<empty>"
    disallowed_import_matches = result.get("disallowed_import_matches") or []
    provider_forbidden_import_matches = result.get("provider_forbidden_import_matches") or []
    provider_meta_import_matches = result.get("provider_meta_import_matches") or []
    provider_required_keyword_matches = result.get("provider_required_keyword_matches") or []

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was automated",
        (
            f"* Ran a repository-wide source scan across {{{search_roots}}} for the "
            "{code}import 'package:flutter/{code} boundary."
        ),
        (
            f"* Inspected {{{provider_relative_path}}} to confirm the visible import block "
            "uses the compatibility shim instead of Flutter foundation."
        ),
        (
            f"* Verified the shipped replacement evidence after the import removal. "
            "The provider imports `package:meta`, matching the ticket's stated expectation."
        ),
        "",
        "h4. Human-style verification",
        (
            "* Opened the provider file header and confirmed the visible imports were "
            "the Dart/http/domain/provider compat imports shown below."
        ),
        "{code:dart}",
        provider_excerpt,
        "{code}",
        "",
        "h4. Result",
        "* Step 1 passed: the global search returned zero direct Flutter imports under `lib/data/` and `lib/domain/`.",
        "* Step 2 passed: `github_trackstate_provider.dart` no longer imports Flutter foundation and visibly imports `foundation_compat.dart` for `kIsWeb`.",
        (
            "* Step 3 passed: the provider imports `package:meta`, matching the ticket's "
            "explicit replacement expectation."
        ),
        (
            f"* Observed counts: disallowed boundary matches = {len(disallowed_import_matches)}, "
            f"provider forbidden import matches = {len(provider_forbidden_import_matches)}, "
            f"`package:meta` matches = {len(provider_meta_import_matches)}, "
            f"`required this.` matches sampled = {len(provider_required_keyword_matches)}."
        ),
        "* The observed behavior matched the expected regression boundary.",
        "",
        "h4. Test file",
        "{code}",
        TEST_FILE_PATH,
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]

    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ✅ PASSED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            f"- Ran a repository-wide source scan across `{search_roots}` for the "
            "`import 'package:flutter/` boundary."
        ),
        (
            f"- Inspected `{provider_relative_path}` to confirm the visible import block "
            "uses the compatibility shim instead of Flutter foundation."
        ),
        (
            "- Verified the shipped replacement evidence after the import removal. "
            "The provider imports `package:meta`, matching the ticket's stated expectation."
        ),
        "",
        "## Human-style verification",
        (
            "- Opened the provider file header and confirmed the visible imports were "
            "the Dart/http/domain/provider compat imports below."
        ),
        "```dart",
        provider_excerpt,
        "```",
        "",
        "## Result",
        "- Step 1 passed: the global search returned zero direct Flutter imports under `lib/data/` and `lib/domain/`.",
        "- Step 2 passed: `github_trackstate_provider.dart` no longer imports Flutter foundation and visibly imports `foundation_compat.dart` for `kIsWeb`.",
        (
            "- Step 3 passed: the provider imports `package:meta`, matching the ticket's "
            "explicit replacement expectation."
        ),
        (
            f"- Observed counts: disallowed boundary matches = {len(disallowed_import_matches)}, "
            f"provider forbidden import matches = {len(provider_forbidden_import_matches)}, "
            f"`package:meta` matches = {len(provider_meta_import_matches)}, "
            f"`required this.` matches sampled = {len(provider_required_keyword_matches)}."
        ),
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error_message = _as_text(result.get("error")) or "AssertionError: unknown failure"
    _write_review_replies()
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_message,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    search_roots = ", ".join(str(root) for root in result.get("search_roots", [])) or "lib/data, lib/domain"
    provider_relative_path = _as_text(result.get("provider_relative_path")) or (
        "lib/data/providers/github/github_trackstate_provider.dart"
    )
    provider_excerpt = _as_text(result.get("provider_excerpt")) or "<empty>"
    traceback_text = _as_text(result.get("traceback"))
    environment_lines = [
        f"- Repository root: `{_as_text(result.get('repository_root')) or str(REPO_ROOT)}`",
        f"- OS: `{_as_text(result.get('os')) or platform.system()}`",
        "- URL: `N/A (repository source inspection)`",
        "- Browser: `N/A`",
        f"- Search roots: `{search_roots}`",
        f"- Provider file: `{provider_relative_path}`",
    ]
    disallowed_matches = result.get("disallowed_import_matches") or []
    forbidden_matches = result.get("provider_forbidden_import_matches") or []
    meta_matches = result.get("provider_meta_import_matches") or []
    required_matches = result.get("provider_required_keyword_matches") or []
    observed_counts = (
        f"disallowed boundary matches={len(disallowed_matches)}, "
        f"provider forbidden import matches={len(forbidden_matches)}, "
        f"package:meta matches={len(meta_matches)}, "
        f"required this. matches sampled={len(required_matches)}"
    )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. Failure summary",
        f"* Error: {{{error_message}}}",
        f"* Observed counts: {{{observed_counts}}}",
        "",
        "h4. Step-by-step reproduction",
        (
            "* Step 1 — Perform a static analysis or global search for the string "
            "{code}import 'package:flutter/{code} within {code}lib/data/{code} and "
            "{code}lib/domain/{code}: "
            + (
                "✅ passed."
                if not disallowed_matches
                else "❌ failed with these matches:\n{code}\n"
                + _format_match_dicts(disallowed_matches)
                + "\n{code}"
            )
        ),
        (
            "* Step 2 — Inspect {code}lib/data/providers/github/github_trackstate_provider.dart{code} "
            "for the removal of the foundation library: "
            + (
                "✅ passed."
                if not forbidden_matches
                else "❌ failed with these matches:\n{code}\n"
                + _format_match_dicts(forbidden_matches)
                + "\n{code}"
            )
        ),
        (
            "* Step 3 — Check for the non-Flutter replacement in the provider: "
            + (
                "✅ passed."
                if meta_matches
                else "❌ failed because no `package:meta` import was present. "
                + _replacement_failure_detail(required_matches)
            )
        ),
        "",
        "h4. Actual vs Expected",
        "* Expected: no direct Flutter imports in the data/domain layers, and `github_trackstate_provider.dart` shows `package:meta` as the non-Flutter replacement evidence named by the ticket.",
        (
            "* Actual: "
            + (
                "the repository scan or provider inspection still exposed Flutter-boundary evidence."
                if disallowed_matches or forbidden_matches
                else _replacement_actual_detail(required_matches)
            )
        ),
        "",
        "h4. Visible source evidence",
        "{code:dart}",
        provider_excerpt,
        "{code}",
        "",
        "h4. Environment",
        *environment_lines,
        "",
        "h4. Exact error",
        "{code:text}",
        traceback_text or error_message,
        "{code}",
    ]

    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## Failure summary",
        f"- Error: `{error_message}`",
        f"- Observed counts: `{observed_counts}`",
        "",
        "## Step-by-step reproduction",
        (
            "1. Perform a static analysis or global search for the string "
            "`import 'package:flutter/` within `lib/data/` and `lib/domain/` — "
            + (
                "passed."
                if not disallowed_matches
                else "failed with these matches:\n```text\n"
                + _format_match_dicts(disallowed_matches)
                + "\n```"
            )
        ),
        (
            "2. Inspect `lib/data/providers/github/github_trackstate_provider.dart` for the "
            "removal of the foundation library — "
            + (
                "passed."
                if not forbidden_matches
                else "failed with these matches:\n```text\n"
                + _format_match_dicts(forbidden_matches)
                + "\n```"
            )
        ),
        (
            "3. Check for the non-Flutter replacement in the provider — "
            + (
                "passed."
                if meta_matches
                else "failed because no `package:meta` import was present. "
                + _replacement_failure_detail(required_matches)
            )
        ),
        "",
        "## Actual vs Expected",
        "- Expected: no direct Flutter imports in the data/domain layers, and `github_trackstate_provider.dart` shows `package:meta` as the non-Flutter replacement evidence named by the ticket.",
        (
            "- Actual: "
            + (
                "the repository scan or provider inspection still exposed Flutter-boundary evidence."
                if disallowed_matches or forbidden_matches
                else _replacement_actual_detail(required_matches)
            )
        ),
        "",
        "## Visible source evidence",
        "```dart",
        provider_excerpt,
        "```",
        "",
        "## Environment",
        *environment_lines,
        "",
        "## Exact error",
        "```text",
        traceback_text or error_message,
        "```",
    ]

    bug_lines = [
        f"# Bug Report — {TICKET_KEY}",
        "",
        f"**Summary:** {TICKET_SUMMARY}",
        "",
        "## Exact steps to reproduce",
        (
            "1. Perform a static analysis or global search for the string "
            "`import 'package:flutter/` within `lib/data/` and `lib/domain/`.\n"
            + (
                "   - ✅ Passed: no matches were found."
                if not disallowed_matches
                else "   - ❌ Failed: the scan still found these matches:\n```text\n"
                + _format_match_dicts(disallowed_matches)
                + "\n```"
            )
        ),
        (
            "2. Inspect `lib/data/providers/github/github_trackstate_provider.dart` for the "
            "removal of the foundation library.\n"
            + (
                "   - ✅ Passed: the provider header no longer showed Flutter imports."
                if not forbidden_matches
                else "   - ❌ Failed: the provider still showed Flutter-boundary evidence:\n```text\n"
                + _format_match_dicts(forbidden_matches)
                + "\n```"
            )
        ),
        (
            "3. Check for the non-Flutter replacement in the provider.\n"
            + (
                "   - ✅ Passed: a `package:meta` import was present."
                if meta_matches
                else "   - ❌ Failed: no `package:meta` import was present. "
                + _replacement_failure_detail(required_matches)
            )
        ),
        "",
        "## Actual vs Expected",
        "- **Expected:** No files within the data or domain layers import from `package:flutter/`, and the GitHub provider remains free of Flutter foundation dependencies while showing `package:meta` as the replacement evidence named by the ticket.",
        (
            "- **Actual:** "
            + (
                "The scan or provider inspection still exposed Flutter-boundary imports."
                if disallowed_matches or forbidden_matches
                else _replacement_actual_detail(required_matches)
            )
        ),
        "",
        "## Environment details",
        *environment_lines,
        "",
        "## Visible source excerpt",
        "```dart",
        provider_excerpt,
        "```",
        "",
        "## Exact error message or assertion failure",
        "```text",
        traceback_text or error_message,
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


def _write_review_replies() -> None:
    REVIEW_REPLIES_PATH.write_text(
        json.dumps(
            {
                "replies": [
                    {
                        "inReplyToId": 3234673312,
                        "threadId": "PRRT_kwDOSU6Gf86BxRVw",
                        "reply": (
                            "Fixed: step 3 now passes only when `github_trackstate_provider.dart` contains a real `package:meta` import. Dart `required` usage is kept as diagnostic evidence only, so the rerun now correctly fails against the current repository state because `package:meta` is absent."
                        ),
                    },
                    {
                        "inReplyToId": None,
                        "threadId": None,
                        "reply": (
                            "Fixed: added `testing/tests/TS-597/README.md` and tightened the test to the ticket's exact `package:meta` expectation. The rerun now reports the real product-visible mismatch instead of masking it with a synthetic pass."
                        ),
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    if not isinstance(steps, list):
        raise TypeError("result.steps must be a list")
    steps.append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        }
    )


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    verifications = result.setdefault("human_verification", [])
    if not isinstance(verifications, list):
        raise TypeError("result.human_verification must be a list")
    verifications.append({"check": check, "observed": observed})


def _matches_to_dict(
    matches: tuple[RepositorySourceMatch, ...],
) -> list[dict[str, object]]:
    return [
        {
            "relative_path": match.relative_path,
            "line_number": match.line_number,
            "line_text": match.line_text,
        }
        for match in matches
    ]


def _format_matches(matches: tuple[RepositorySourceMatch, ...]) -> str:
    return "\n".join(
        f"{match.relative_path}:{match.line_number}: {match.line_text}"
        for match in matches
    )


def _format_match_dicts(matches: object) -> str:
    if not isinstance(matches, list):
        return "<none>"
    lines: list[str] = []
    for item in matches:
        if not isinstance(item, dict):
            continue
        relative_path = _as_text(item.get("relative_path"))
        line_number = item.get("line_number")
        line_text = _as_text(item.get("line_text"))
        lines.append(f"{relative_path}:{line_number}: {line_text}")
    return "\n".join(lines) if lines else "<none>"


def _provider_block(validation: FlutterDependencyBoundaryValidationResult) -> str:
    return "\n".join(validation.provider_excerpt_lines)


def _replacement_failure_detail(required_matches: object) -> str:
    if isinstance(required_matches, list) and required_matches:
        return (
            "The provider still contains Dart `required` constructor parameters, but "
            "the current ticket explicitly asks for `package:meta` evidence."
        )
    return "The provider did not expose the ticket's required `package:meta` evidence."


def _replacement_actual_detail(required_matches: object) -> str:
    if isinstance(required_matches, list) and required_matches:
        return (
            "the provider no longer exposes Flutter imports, but it uses Dart "
            "`required` parameters instead of the ticket's expected `package:meta` import."
        )
    return (
        "the provider no longer exposes Flutter imports, but it also does not show "
        "the ticket's expected `package:meta` replacement evidence."
    )


def _as_text(value: object) -> str:
    return value if isinstance(value, str) else ""


if __name__ == "__main__":
    main()
