from __future__ import annotations

import json
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Callable
from urllib.parse import quote

import yaml

from testing.components.pages.github_repository_file_page import (
    GitHubRepositoryFileObservation,
    GitHubRepositoryFilePage,
)
from testing.core.config.github_workflow_trigger_isolation_config import (
    GitHubWorkflowTriggerIsolationConfig,
)
from testing.core.interfaces.github_api_client import GitHubApiClient
from testing.core.interfaces.github_workflow_run_log_reader import (
    GitHubWorkflowRunLogReader,
)
from testing.core.interfaces.github_workflow_trigger_isolation_probe import (
    GitHubWorkflowTriggerIsolationObservation,
    WorkflowDefinitionObservation,
    WorkflowRunObservation,
    WorkflowRunTagEvidenceObservation,
)

FilePageFactory = Callable[[], AbstractContextManager[GitHubRepositoryFilePage]]
SEMVER_TAG_PATTERN = re.compile(r"\bv\d+\.\d+\.\d+\b")


class GitHubWorkflowTriggerIsolationProbeService:
    def __init__(
        self,
        config: GitHubWorkflowTriggerIsolationConfig,
        *,
        github_api_client: GitHubApiClient,
        workflow_run_log_reader: GitHubWorkflowRunLogReader,
        file_page_factory: FilePageFactory,
        screenshot_directory: Path | None = None,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client
        self._workflow_run_log_reader = workflow_run_log_reader
        self._file_page_factory = file_page_factory
        self._screenshot_directory = screenshot_directory

    def validate(self) -> GitHubWorkflowTriggerIsolationObservation:
        repository_metadata = self._load_json(
            endpoint=f"/repos/{self._config.repository}"
        )
        default_branch = self._read_string(
            repository_metadata, "default_branch"
        ) or self._config.default_branch
        current_default_branch_sha = self._load_branch_sha(default_branch)

        apple_release = self._load_workflow_observation(
            workflow_name=self._config.apple_workflow_name,
            workflow_file=self._config.apple_workflow_file,
            workflow_path=self._config.apple_workflow_path,
            default_branch=default_branch,
            expected_page_texts=(
                self._config.apple_workflow_name,
                self._config.expected_semver_tag_pattern,
                "v1.2.3",
            ),
            screenshot_name="ts709_apple_workflow_page.png",
        )
        main_ci = self._load_workflow_observation(
            workflow_name=self._config.main_ci_workflow_name,
            workflow_file=self._config.main_ci_workflow_file,
            workflow_path=self._config.main_ci_workflow_path,
            default_branch=default_branch,
            expected_page_texts=(
                self._config.main_ci_workflow_name,
                default_branch,
                "push",
            ),
            screenshot_name="ts709_flutter_ci_page.png",
        )

        cutoff = self._parse_timestamp(apple_release.updated_at)
        apple_push_main_after_cutoff = self._filter_push_main_runs(
            apple_release.recent_runs,
            branch=default_branch,
            minimum_timestamp=cutoff,
        )
        main_ci_push_main_after_cutoff = self._filter_push_main_runs(
            main_ci.recent_runs,
            branch=default_branch,
            minimum_timestamp=cutoff,
        )
        semantic_tags_by_sha = self._load_semantic_tags_by_sha()

        return GitHubWorkflowTriggerIsolationObservation(
            repository=self._config.repository,
            default_branch=default_branch,
            current_default_branch_sha=current_default_branch_sha,
            apple_release=apple_release,
            main_ci=main_ci,
            cutoff_timestamp=apple_release.updated_at,
            apple_push_main_after_cutoff=apple_push_main_after_cutoff,
            main_ci_push_main_after_cutoff=main_ci_push_main_after_cutoff,
            apple_push_main_current_sha=self._filter_push_main_runs(
                apple_release.recent_runs,
                branch=default_branch,
                head_sha=current_default_branch_sha,
            ),
            main_ci_push_main_current_sha=self._filter_push_main_runs(
                main_ci.recent_runs,
                branch=default_branch,
                head_sha=current_default_branch_sha,
            ),
            apple_push_semver_tag_evidence=self._collect_semver_tag_run_evidence(
                apple_release.recent_runs,
                semantic_tags_by_sha=semantic_tags_by_sha,
            ),
        )

    def _load_workflow_observation(
        self,
        *,
        workflow_name: str,
        workflow_file: str,
        workflow_path: str,
        default_branch: str,
        expected_page_texts: tuple[str, ...],
        screenshot_name: str,
    ) -> WorkflowDefinitionObservation:
        metadata = self._load_json(
            endpoint=(
                f"/repos/{self._config.repository}/actions/workflows/"
                f"{quote(workflow_file, safe='')}"
            )
        )
        raw_file_text = self._github_api_client.request_text(
            endpoint=(
                f"/repos/{self._config.repository}/contents/"
                f"{quote(workflow_path, safe='/')}?ref={quote(default_branch, safe='')}"
            ),
            field_args=["-H", "Accept: application/vnd.github.raw+json"],
        )
        push_branches, push_tags, workflow_dispatch_enabled = self._parse_workflow_triggers(
            raw_file_text
        )
        ui_observation = self._load_ui_observation(
            default_branch=default_branch,
            workflow_path=workflow_path,
            expected_page_texts=expected_page_texts,
            screenshot_name=screenshot_name,
        )
        recent_runs = self._load_recent_runs(workflow_file)

        return WorkflowDefinitionObservation(
            workflow_name=workflow_name,
            workflow_file=workflow_file,
            workflow_path=workflow_path,
            state=self._read_string(metadata, "state") or "",
            html_url=self._read_string(metadata, "html_url") or "",
            updated_at=self._read_string(metadata, "updated_at"),
            push_branches=push_branches,
            push_tags=push_tags,
            workflow_dispatch_enabled=workflow_dispatch_enabled,
            semantic_tag_hint_present="v1.2.3" in raw_file_text,
            raw_file_text=raw_file_text,
            recent_runs=recent_runs,
            ui_url=ui_observation.url if ui_observation else None,
            ui_body_text=ui_observation.body_text if ui_observation else "",
            ui_error=None if ui_observation else "GitHub file page did not load.",
            ui_screenshot_path=(
                ui_observation.screenshot_path if ui_observation else None
            ),
        )

    def _load_ui_observation(
        self,
        *,
        default_branch: str,
        workflow_path: str,
        expected_page_texts: tuple[str, ...],
        screenshot_name: str,
    ) -> GitHubRepositoryFileObservation | None:
        screenshot_path: str | None = None
        if self._screenshot_directory is not None:
            screenshot_path = str(self._screenshot_directory / screenshot_name)

        with self._file_page_factory() as file_page:
            return file_page.open_file(
                repository=self._config.repository,
                branch=default_branch,
                file_path=workflow_path,
                expected_texts=expected_page_texts,
                screenshot_path=screenshot_path,
                timeout_seconds=self._config.ui_timeout_seconds,
            )

    def _load_branch_sha(self, branch: str) -> str:
        payload = self._load_json(
            endpoint=(
                f"/repos/{self._config.repository}/branches/"
                f"{quote(branch, safe='')}"
            )
        )
        commit = payload.get("commit")
        if isinstance(commit, dict):
            sha = commit.get("sha")
            if isinstance(sha, str) and sha.strip():
                return sha.strip()
        raise AssertionError(
            f"GitHub did not expose a commit SHA for {self._config.repository}@{branch}."
        )

    def _load_recent_runs(self, workflow_file: str) -> list[WorkflowRunObservation]:
        payload = self._load_json(
            endpoint=(
                f"/repos/{self._config.repository}/actions/workflows/"
                f"{quote(workflow_file, safe='')}/runs"
                f"?per_page={self._config.recent_runs_limit}"
            )
        )
        raw_runs = payload.get("workflow_runs")
        if not isinstance(raw_runs, list):
            return []

        runs: list[WorkflowRunObservation] = []
        for entry in raw_runs:
            if not isinstance(entry, dict):
                continue
            run_id = entry.get("id")
            if not isinstance(run_id, int):
                continue
            runs.append(
                WorkflowRunObservation(
                    id=run_id,
                    name=self._read_string(entry, "name") or "",
                    event=self._read_string(entry, "event") or "",
                    head_branch=self._read_string(entry, "head_branch"),
                    head_sha=self._read_string(entry, "head_sha"),
                    status=self._read_string(entry, "status"),
                    conclusion=self._read_string(entry, "conclusion"),
                    html_url=self._read_string(entry, "html_url") or "",
                    created_at=self._read_string(entry, "created_at"),
                    display_title=self._read_string(entry, "display_title"),
                )
            )
        return runs

    def _load_semantic_tags_by_sha(self) -> dict[str, list[str]]:
        payload = json.loads(
            self._github_api_client.request_text(
                endpoint=f"/repos/{self._config.repository}/git/matching-refs/tags/v"
            )
        )
        if not isinstance(payload, list):
            raise AssertionError(
                "GitHub did not return a tag-ref list for semantic version lookups."
            )

        tags_by_sha: dict[str, list[str]] = {}
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            ref = entry.get("ref")
            object_payload = entry.get("object")
            if not isinstance(ref, str) or not isinstance(object_payload, dict):
                continue
            sha = object_payload.get("sha")
            if not isinstance(sha, str) or not sha.strip():
                continue
            tag_name = ref.removeprefix("refs/tags/").strip()
            if not SEMVER_TAG_PATTERN.fullmatch(tag_name):
                continue
            tags_by_sha.setdefault(sha.strip(), []).append(tag_name)

        for tags in tags_by_sha.values():
            tags.sort()
        return tags_by_sha

    def _collect_semver_tag_run_evidence(
        self,
        runs: list[WorkflowRunObservation],
        *,
        semantic_tags_by_sha: dict[str, list[str]],
    ) -> list[WorkflowRunTagEvidenceObservation]:
        evidence: list[WorkflowRunTagEvidenceObservation] = []
        for run in runs:
            if run.event != "push" or run.head_sha is None:
                continue
            candidate_tags = semantic_tags_by_sha.get(run.head_sha, [])
            if not candidate_tags:
                continue
            log_text = self._workflow_run_log_reader.read_run_log(run.id)
            log_tags = sorted({match.group(0) for match in SEMVER_TAG_PATTERN.finditer(log_text)})
            matched_tags = [tag for tag in candidate_tags if tag in log_tags]
            if not matched_tags:
                continue
            evidence.append(
                WorkflowRunTagEvidenceObservation(
                    run=run,
                    semantic_tags=matched_tags,
                    log_excerpt=self._extract_tag_log_excerpt(log_text, matched_tags),
                )
            )
            if len(evidence) >= 3:
                break
        return evidence

    def _load_json(self, *, endpoint: str) -> dict[str, Any]:
        payload = json.loads(self._github_api_client.request_text(endpoint=endpoint))
        if not isinstance(payload, dict):
            raise AssertionError(
                f"Expected GitHub API payload for {endpoint} to decode to a mapping."
            )
        return payload

    def _parse_workflow_triggers(self, raw_file_text: str) -> tuple[list[str], list[str], bool]:
        parsed = yaml.load(raw_file_text, Loader=yaml.BaseLoader)
        if not isinstance(parsed, dict):
            return ([], [], False)

        on_payload = parsed.get("on")
        if not isinstance(on_payload, dict):
            return ([], [], False)

        push_payload = on_payload.get("push")
        push_branches = self._string_list_from_payload(push_payload, "branches")
        push_tags = self._string_list_from_payload(push_payload, "tags")
        return (push_branches, push_tags, "workflow_dispatch" in on_payload)

    def _string_list_from_payload(
        self,
        payload: object,
        key: str,
    ) -> list[str]:
        if not isinstance(payload, dict):
            return []
        raw_value = payload.get(key)
        if isinstance(raw_value, str) and raw_value.strip():
            return [raw_value.strip()]
        if not isinstance(raw_value, list):
            return []
        values: list[str] = []
        for item in raw_value:
            if isinstance(item, str) and item.strip():
                values.append(item.strip())
        return values

    def _filter_push_main_runs(
        self,
        runs: list[WorkflowRunObservation],
        *,
        branch: str,
        minimum_timestamp: datetime | None = None,
        head_sha: str | None = None,
    ) -> list[WorkflowRunObservation]:
        filtered: list[WorkflowRunObservation] = []
        for run in runs:
            if run.event != "push" or run.head_branch != branch:
                continue
            if head_sha is not None and run.head_sha != head_sha:
                continue
            created_at = self._parse_timestamp(run.created_at)
            if minimum_timestamp is not None and (
                created_at is None or created_at < minimum_timestamp
            ):
                continue
            filtered.append(run)
        return filtered

    @staticmethod
    def _extract_tag_log_excerpt(log_text: str, tags: list[str]) -> str:
        excerpt_lines: list[str] = []
        for line in log_text.splitlines():
            if any(tag in line for tag in tags):
                excerpt_lines.append(line.strip())
            if len(excerpt_lines) >= 4:
                break
        if excerpt_lines:
            return "\n".join(excerpt_lines)
        return "No semantic tag lines were captured from the workflow log."

    @staticmethod
    def _read_string(payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime | None:
        if value is None or not value.strip():
            return None
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
