from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any

from testing.components.services.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateError,
    GitHubAccessibilityPullRequestGateProbeService,
)
from testing.core.interfaces.github_accessibility_branch_protection_merge_block_probe import (
    GitHubAccessibilityBranchProtectionMergeBlockObservation,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateObservation,
)


class GitHubAccessibilityBranchProtectionMergeBlockProbeService(
    GitHubAccessibilityPullRequestGateProbeService
):
    def validate(self) -> GitHubAccessibilityBranchProtectionMergeBlockObservation:
        repository_info = self._read_json_object(f"/repos/{self._config.repository}")
        default_branch = self._default_branch(repository_info)
        workflow = self._select_workflow()
        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, int):
            raise GitHubAccessibilityPullRequestGateError(
                "TS-936 could not resolve a numeric workflow ID for "
                f"{self._config.target_workflow_path}."
            )

        workflow_text = self._read_workflow_text(
            self._config.target_workflow_path,
            default_branch,
        )
        workflow_contract = self._workflow_contract(workflow_text)
        required_rules = self._read_required_rules()
        pull_request_observation = self._create_and_observe_pull_request(workflow_id)
        observed_run_jobs = self._coerce_job_observations(
            pull_request_observation.get("observed_run_jobs")
        )

        gate = GitHubAccessibilityPullRequestGateObservation(
            repository=self._config.repository,
            default_branch=default_branch,
            target_workflow_name=self._config.target_workflow_name,
            target_workflow_path=self._config.target_workflow_path,
            target_workflow_id=workflow_id,
            target_workflow_present_on_default_branch=True,
            target_workflow_declares_pull_request_trigger=workflow_contract.declares_pull_request_trigger,
            target_workflow_job_names=workflow_contract.job_names,
            target_workflow_step_names=workflow_contract.step_names,
            target_workflow_accessibility_job_names=workflow_contract.accessibility_job_names,
            target_workflow_downstream_job_names=workflow_contract.downstream_job_names,
            target_workflow_downstream_job_depends_on_accessibility=(
                workflow_contract.downstream_job_depends_on_accessibility
            ),
            target_workflow=workflow_contract,
            pull_request_number=int(pull_request_observation["pull_request_number"]),
            pull_request_url=str(pull_request_observation["pull_request_url"]),
            pull_request_checks_url=str(pull_request_observation["pull_request_checks_url"]),
            pull_request_head_branch=str(pull_request_observation["pull_request_head_branch"]),
            pull_request_head_sha=self._optional_string(
                pull_request_observation.get("pull_request_head_sha")
            ),
            pull_request_probe_path=str(pull_request_observation["pull_request_probe_path"]),
            probe_render_host_path=str(pull_request_observation["probe_render_host_path"]),
            probe_rendered_in_application=bool(
                pull_request_observation["probe_rendered_in_application"]
            ),
            pull_request_file_paths=list(pull_request_observation["pull_request_file_paths"]),
            pull_request_state=self._optional_string(
                pull_request_observation.get("pull_request_state")
            ),
            pull_request_mergeable_state=self._optional_string(
                pull_request_observation.get("pull_request_mergeable_state")
            ),
            pull_request_status_state=self._optional_string(
                pull_request_observation.get("pull_request_status_state")
            ),
            latest_pull_request_run_id=self._optional_int(
                pull_request_observation.get("latest_pull_request_run_id")
            ),
            latest_pull_request_run_url=self._optional_string(
                pull_request_observation.get("latest_pull_request_run_url")
            ),
            latest_pull_request_run_event=self._optional_string(
                pull_request_observation.get("latest_pull_request_run_event")
            ),
            latest_pull_request_run_status=self._optional_string(
                pull_request_observation.get("latest_pull_request_run_status")
            ),
            latest_pull_request_run_conclusion=self._optional_string(
                pull_request_observation.get("latest_pull_request_run_conclusion")
            ),
            observed_branch_run_names=list(pull_request_observation["observed_branch_run_names"]),
            observed_branch_run_urls=list(pull_request_observation["observed_branch_run_urls"]),
            observed_branch_run_statuses=list(
                pull_request_observation["observed_branch_run_statuses"]
            ),
            observed_branch_run_conclusions=list(
                pull_request_observation["observed_branch_run_conclusions"]
            ),
            observed_run_jobs=observed_run_jobs,
            observed_job_names=list(pull_request_observation["observed_job_names"]),
            observed_step_names=list(pull_request_observation["observed_step_names"]),
            observed_status_check_names=list(
                pull_request_observation["observed_status_check_names"]
            ),
            observed_status_check_workflow_names=list(
                pull_request_observation["observed_status_check_workflow_names"]
            ),
            failed_status_check_names=list(
                pull_request_observation["failed_status_check_names"]
            ),
            failed_status_check_workflow_names=list(
                pull_request_observation["failed_status_check_workflow_names"]
            ),
            accessibility_status_check_name=self._optional_string(
                pull_request_observation.get("accessibility_status_check_name")
            ),
            accessibility_status_check_workflow_name=self._optional_string(
                pull_request_observation.get("accessibility_status_check_workflow_name")
            ),
            accessibility_status_check_status=self._optional_string(
                pull_request_observation.get("accessibility_status_check_status")
            ),
            accessibility_status_check_conclusion=self._optional_string(
                pull_request_observation.get("accessibility_status_check_conclusion")
            ),
            accessibility_status_check_url=self._optional_string(
                pull_request_observation.get("accessibility_status_check_url")
            ),
            matched_accessibility_markers=list(
                pull_request_observation["matched_accessibility_markers"]
            ),
            matched_contrast_markers=list(pull_request_observation["matched_contrast_markers"]),
            matched_semantic_markers=list(pull_request_observation["matched_semantic_markers"]),
            run_log_matched_accessibility_markers=list(
                pull_request_observation["run_log_matched_accessibility_markers"]
            ),
            run_log_matched_contrast_markers=list(
                pull_request_observation["run_log_matched_contrast_markers"]
            ),
            run_log_matched_semantic_markers=list(
                pull_request_observation["run_log_matched_semantic_markers"]
            ),
            run_log_mentions_accessibility=bool(
                pull_request_observation["run_log_mentions_accessibility"]
            ),
            run_log_mentions_contrast_issue=bool(
                pull_request_observation["run_log_mentions_contrast_issue"]
            ),
            run_log_mentions_semantic_issue=bool(
                pull_request_observation["run_log_mentions_semantic_issue"]
            ),
            run_log_excerpt=str(pull_request_observation["run_log_excerpt"]),
            run_log_error=self._optional_string(pull_request_observation.get("run_log_error")),
            runtime_accessibility_surface_present=bool(
                pull_request_observation["runtime_accessibility_surface_present"]
            ),
            runtime_accessibility_surface_summary=str(
                pull_request_observation["runtime_accessibility_surface_summary"]
            ),
            probe_contains_low_contrast_indicator=bool(
                pull_request_observation["probe_contains_low_contrast_indicator"]
            ),
            probe_contains_semantic_label_indicator=bool(
                pull_request_observation["probe_contains_semantic_label_indicator"]
            ),
            probe_semantic_label=str(pull_request_observation["probe_semantic_label"]),
            probe_contrast_technique=str(pull_request_observation["probe_contrast_technique"]),
            cleanup_closed_pull_request=bool(
                pull_request_observation["cleanup_closed_pull_request"]
            ),
            cleanup_deleted_branch=bool(
                pull_request_observation["cleanup_deleted_branch"]
            ),
            default_branch_probe_host_present=bool(
                pull_request_observation.get("default_branch_probe_host_present")
            ),
            default_branch_probe_host_summary=str(
                pull_request_observation.get("default_branch_probe_host_summary", "")
            ),
        )

        return GitHubAccessibilityBranchProtectionMergeBlockObservation(
            gate=gate,
            required_rule_descriptions=list(required_rules["descriptions"]),
            required_check_contexts=list(required_rules["contexts"]),
            repository_declares_accessibility_required_check=bool(
                required_rules["accessibility_required"]
            ),
            pull_request_mergeable=self._optional_string(
                pull_request_observation.get("pull_request_mergeable")
            ),
            pull_request_merge_state_status=self._optional_string(
                pull_request_observation.get("pull_request_merge_state_status")
            ),
        )

    def _create_and_observe_pull_request(self, workflow_id: int) -> dict[str, object]:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts936-"))
        pull_request_number: int | None = None
        branch_name = self._unique_branch_name()
        branch_pushed = False
        cleanup_closed_pull_request = False
        cleanup_deleted_branch = False
        observation: dict[str, object] | None = None
        (
            default_branch_probe_host_present,
            default_branch_probe_host_summary,
        ) = self._default_branch_probe_host_details(self._config.base_branch)

        try:
            self._run_command(["gh", "auth", "setup-git"], cwd=None)
            self._run_command(
                [
                    "git",
                    "clone",
                    "--quiet",
                    self._origin_clone_url(),
                    str(temp_repository_root),
                ],
                cwd=None,
            )
            self._run_command(
                [
                    "git",
                    "checkout",
                    "-b",
                    branch_name,
                    f"origin/{self._config.base_branch}",
                ],
                cwd=temp_repository_root,
            )
            self._run_command(["git", "config", "user.name", "ai-teammate"], cwd=temp_repository_root)
            self._run_command(
                ["git", "config", "user.email", "agent.ai.native@gmail.com"],
                cwd=temp_repository_root,
            )

            probe_source = self._probe_source()
            probe_file = temp_repository_root / self._config.probe_path
            probe_file.parent.mkdir(parents=True, exist_ok=True)
            probe_file.write_text(probe_source, encoding="utf-8")
            render_host_file = temp_repository_root / self._config.probe_render_host_path
            render_host_original_source = render_host_file.read_text(encoding="utf-8")
            render_host_source = self._inject_probe_into_render_host(render_host_original_source)
            render_host_file.write_text(render_host_source, encoding="utf-8")

            self._run_command(
                ["git", "add", self._config.probe_path, self._config.probe_render_host_path],
                cwd=temp_repository_root,
            )
            self._run_command(
                ["git", "commit", "-m", self._config.commit_message],
                cwd=temp_repository_root,
            )

            started_at = time.time()
            self._run_command(
                ["git", "push", "--set-upstream", "origin", branch_name],
                cwd=temp_repository_root,
            )
            branch_pushed = True

            pr_url = self._run_command(
                [
                    "gh",
                    "pr",
                    "create",
                    "--repo",
                    self._config.repository,
                    "--base",
                    self._config.base_branch,
                    "--head",
                    branch_name,
                    "--title",
                    self._config.pull_request_title,
                    "--body",
                    self._config.pull_request_body,
                ],
                cwd=temp_repository_root,
            ).stdout.strip()
            pull_request_number = self._extract_pull_request_number(pr_url)
            pull_request = self._wait_for_pull_request(pull_request_number)
            pull_request_files = self._read_pull_request_files(pull_request_number)
            head_sha = self._optional_string(((pull_request.get("head") or {}).get("sha")))
            run_observation = self._wait_for_pull_request_run(
                workflow_id,
                branch_name,
                started_at,
            )
            run_id = self._optional_int(run_observation.get("latest_pull_request_run_id"))
            jobs = self._read_jobs(run_id) if run_id is not None else []
            surface_observation = self._wait_for_pull_request_surface(
                pull_request_number,
                head_sha=head_sha,
            )
            accessibility_check = self._find_accessibility_status_check(
                surface_observation["status_checks"]
            )
            run_log_text, run_log_error = self._try_read_run_log(run_id)
            run_log_matched_accessibility_markers = self._matched_markers(
                run_log_text,
                self._config.expected_accessibility_markers,
            )
            run_log_matched_contrast_markers = self._matched_markers(
                run_log_text,
                self._config.contrast_evidence_markers,
            )
            run_log_matched_semantic_markers = self._matched_markers(
                run_log_text,
                self._config.semantic_evidence_markers,
            )
            evidence_text = "\n".join(
                [
                    *surface_observation["status_check_names"],
                    *surface_observation["status_check_workflow_names"],
                    *self._job_names(jobs),
                    *self._step_names(jobs),
                    run_log_text,
                ]
            )
            matched_accessibility_markers = self._matched_markers(
                evidence_text,
                self._config.expected_accessibility_markers,
            )
            matched_contrast_markers = self._matched_markers(
                evidence_text,
                self._config.contrast_evidence_markers,
            )
            matched_semantic_markers = self._matched_markers(
                evidence_text,
                self._config.semantic_evidence_markers,
            )
            probe_semantic_label = self._extract_probe_semantic_label(probe_source)
            runtime_accessibility_surface_summary = (
                self._extract_runtime_accessibility_surface_summary(run_log_text)
            )

            observation = {
                "pull_request_number": pull_request_number,
                "pull_request_url": pr_url,
                "pull_request_checks_url": f"{pr_url}/checks",
                "pull_request_head_branch": branch_name,
                "pull_request_head_sha": head_sha,
                "pull_request_probe_path": self._config.probe_path,
                "probe_render_host_path": self._config.probe_render_host_path,
                "probe_rendered_in_application": (
                    self._config.probe_path in pull_request_files
                    and (
                        self._config.probe_render_host_path in pull_request_files
                        or default_branch_probe_host_present
                        or self._render_host_renders_probe(render_host_original_source)
                        or self._render_host_renders_probe(render_host_source)
                    )
                ),
                "pull_request_file_paths": pull_request_files,
                "pull_request_state": self._optional_string(pull_request.get("state")),
                "pull_request_mergeable_state": surface_observation[
                    "pull_request_mergeable_state"
                ],
                "pull_request_status_state": surface_observation["pull_request_status_state"],
                "pull_request_mergeable": surface_observation["pull_request_mergeable"],
                "pull_request_merge_state_status": surface_observation[
                    "pull_request_merge_state_status"
                ],
                **run_observation,
                "observed_run_jobs": self._to_workflow_job_observations(jobs),
                "observed_job_names": self._job_names(jobs),
                "observed_step_names": self._step_names(jobs),
                "observed_status_check_names": surface_observation["status_check_names"],
                "observed_status_check_workflow_names": surface_observation[
                    "status_check_workflow_names"
                ],
                "failed_status_check_names": surface_observation["failed_status_check_names"],
                "failed_status_check_workflow_names": surface_observation[
                    "failed_status_check_workflow_names"
                ],
                "accessibility_status_check_name": None
                if accessibility_check is None
                else accessibility_check["name"],
                "accessibility_status_check_workflow_name": None
                if accessibility_check is None
                else accessibility_check["workflow_name"],
                "accessibility_status_check_status": None
                if accessibility_check is None
                else accessibility_check["status"],
                "accessibility_status_check_conclusion": None
                if accessibility_check is None
                else accessibility_check["conclusion"],
                "accessibility_status_check_url": None
                if accessibility_check is None
                else accessibility_check["details_url"],
                "matched_accessibility_markers": matched_accessibility_markers,
                "matched_contrast_markers": matched_contrast_markers,
                "matched_semantic_markers": matched_semantic_markers,
                "run_log_matched_accessibility_markers": run_log_matched_accessibility_markers,
                "run_log_matched_contrast_markers": run_log_matched_contrast_markers,
                "run_log_matched_semantic_markers": run_log_matched_semantic_markers,
                "run_log_mentions_accessibility": bool(run_log_matched_accessibility_markers),
                "run_log_mentions_contrast_issue": bool(run_log_matched_contrast_markers),
                "run_log_mentions_semantic_issue": bool(run_log_matched_semantic_markers),
                "run_log_excerpt": self._extract_log_excerpt(run_log_text, evidence_text),
                "run_log_error": run_log_error,
                "runtime_accessibility_surface_present": bool(
                    runtime_accessibility_surface_summary
                ),
                "runtime_accessibility_surface_summary": runtime_accessibility_surface_summary,
                "probe_contains_low_contrast_indicator": self._probe_has_low_contrast_indicator(
                    probe_source
                ),
                "probe_contains_semantic_label_indicator": probe_semantic_label is not None,
                "probe_semantic_label": probe_semantic_label or "",
                "probe_contrast_technique": self._probe_contrast_technique(probe_source),
                "cleanup_closed_pull_request": False,
                "cleanup_deleted_branch": False,
                "default_branch_probe_host_present": default_branch_probe_host_present,
                "default_branch_probe_host_summary": default_branch_probe_host_summary,
            }
        finally:
            if pull_request_number is not None:
                cleanup_closed_pull_request = self._close_pull_request(pull_request_number)
            if branch_pushed:
                cleanup_deleted_branch = self._delete_branch(
                    branch_name,
                    cwd=temp_repository_root,
                )
            if temp_repository_root.exists():
                shutil.rmtree(temp_repository_root)
            if observation is not None:
                observation["cleanup_closed_pull_request"] = cleanup_closed_pull_request
                observation["cleanup_deleted_branch"] = cleanup_deleted_branch

        if observation is None:
            raise GitHubAccessibilityPullRequestGateError(
                "TS-936 did not produce a disposable pull request observation."
            )
        return observation

    def _wait_for_pull_request_surface(
        self,
        pull_request_number: int,
        *,
        head_sha: str | None,
    ) -> dict[str, object]:
        deadline = time.time() + self._config.pull_request_timeout_seconds
        latest_state = {
            "pull_request_mergeable_state": None,
            "pull_request_status_state": None,
            "pull_request_mergeable": None,
            "pull_request_merge_state_status": None,
            "status_checks": [],
            "status_check_names": [],
            "status_check_workflow_names": [],
            "failed_status_check_names": [],
            "failed_status_check_workflow_names": [],
        }

        while time.time() < deadline:
            pull_request = self._read_json_object(
                f"/repos/{self._config.repository}/pulls/{pull_request_number}"
            )
            sha = self._optional_string(((pull_request.get("head") or {}).get("sha"))) or head_sha
            mergeable_state = self._optional_string(pull_request.get("mergeable_state"))
            status_state = self._read_check_runs_state(sha) if sha else None
            surface = self._read_pull_request_status_surface(pull_request_number)
            latest_state = {
                "pull_request_mergeable_state": mergeable_state,
                "pull_request_status_state": status_state,
                "pull_request_mergeable": surface["pull_request_mergeable"],
                "pull_request_merge_state_status": surface["pull_request_merge_state_status"],
                "status_checks": surface["status_checks"],
                "status_check_names": surface["status_check_names"],
                "status_check_workflow_names": surface["status_check_workflow_names"],
                "failed_status_check_names": surface["failed_status_check_names"],
                "failed_status_check_workflow_names": surface[
                    "failed_status_check_workflow_names"
                ],
            }
            if (
                mergeable_state
                and mergeable_state != "unknown"
                and status_state
                and status_state != "pending"
                and surface["pull_request_merge_state_status"]
            ):
                return latest_state
            time.sleep(self._config.poll_interval_seconds)
        return latest_state

    def _read_pull_request_status_surface(
        self,
        pull_request_number: int,
    ) -> dict[str, object]:
        payload = json.loads(
            self._run_command(
                [
                    "gh",
                    "pr",
                    "view",
                    str(pull_request_number),
                    "--repo",
                    self._config.repository,
                    "--json",
                    "number,mergeable,mergeStateStatus,statusCheckRollup,reviewDecision,isDraft,headRefName",
                ],
                cwd=None,
            ).stdout
        )
        if not isinstance(payload, dict):
            raise GitHubAccessibilityPullRequestGateError(
                f"TS-936 expected gh pr view to return an object: {payload!r}"
            )
        normalized_checks = self._normalize_status_checks(payload.get("statusCheckRollup"))
        return {
            "pull_request_mergeable": self._optional_string(payload.get("mergeable")),
            "pull_request_merge_state_status": self._optional_string(
                payload.get("mergeStateStatus")
            ),
            "status_checks": normalized_checks,
            "status_check_names": self._dedupe(
                [
                    check["name"]
                    for check in normalized_checks
                    if isinstance(check.get("name"), str)
                ]
            ),
            "status_check_workflow_names": self._dedupe(
                [
                    check["workflow_name"]
                    for check in normalized_checks
                    if isinstance(check.get("workflow_name"), str)
                ]
            ),
            "failed_status_check_names": self._dedupe(
                [
                    check["name"]
                    for check in normalized_checks
                    if isinstance(check.get("name"), str)
                    and check.get("conclusion")
                    in {"failure", "cancelled", "timed_out", "action_required"}
                ]
            ),
            "failed_status_check_workflow_names": self._dedupe(
                [
                    check["workflow_name"]
                    for check in normalized_checks
                    if isinstance(check.get("workflow_name"), str)
                    and check.get("conclusion")
                    in {"failure", "cancelled", "timed_out", "action_required"}
                ]
            ),
        }

    def _read_required_rules(self) -> dict[str, object]:
        contexts: list[str] = []
        descriptions: list[str] = []

        try:
            effective_rules = self._read_json_array(
                f"/repos/{self._config.repository}/rules/branches/{self._config.base_branch}"
            )
        except GitHubAccessibilityPullRequestGateError:
            effective_rules = []

        for rule in effective_rules:
            if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
                continue
            parameter_map = rule.get("parameters")
            extracted = self._collect_required_status_check_contexts(
                parameter_map if isinstance(parameter_map, dict) else {}
            )
            if extracted:
                contexts.extend(extracted)
                descriptions.append(f"effective_branch_rules.required_status_checks: {extracted}")

        if not contexts:
            try:
                branch_protection = self._read_json_object(
                    f"/repos/{self._config.repository}/branches/{self._config.base_branch}/protection"
                )
            except GitHubAccessibilityPullRequestGateError:
                branch_protection = {}
            required_status_checks = branch_protection.get("required_status_checks")
            extracted = self._collect_required_status_check_contexts(
                required_status_checks if isinstance(required_status_checks, dict) else {}
            )
            if extracted:
                contexts.extend(extracted)
                descriptions.append(f"branch_protection.required_status_checks: {extracted}")

        unique_contexts = self._dedupe(contexts)
        return {
            "descriptions": self._dedupe(descriptions),
            "contexts": unique_contexts,
            "accessibility_required": any(
                self._contains_any_marker(context, self._config.accessibility_job_markers)
                for context in unique_contexts
            ),
        }

    def _collect_required_status_check_contexts(
        self,
        payload: dict[str, Any],
    ) -> list[str]:
        values: list[str] = []
        for key in ("contexts", "required_status_checks", "checks"):
            raw_entries = payload.get(key)
            if not isinstance(raw_entries, list):
                continue
            for entry in raw_entries:
                if isinstance(entry, str) and entry.strip():
                    values.append(entry.strip())
                    continue
                if not isinstance(entry, dict):
                    continue
                context = self._optional_string(entry.get("context"))
                if context is not None:
                    values.append(context)
                    continue
                name = self._optional_string(entry.get("name"))
                if name is not None:
                    values.append(name)
        return self._dedupe(values)
