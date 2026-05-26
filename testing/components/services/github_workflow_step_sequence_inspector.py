from __future__ import annotations

import base64
import json
from pathlib import Path
import re
from typing import Any

import yaml

from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)
from testing.core.interfaces.github_workflow_step_sequence_inspector import (
    GitHubWorkflowRunStepObservation,
    GitHubWorkflowStepContractObservation,
    GitHubWorkflowStepSequenceObservation,
)


class GitHubWorkflowStepSequenceInspectorError(RuntimeError):
    pass


class GitHubWorkflowStepSequenceInspectorService:
    def __init__(self, *, github_api_client: GitHubApiClient) -> None:
        self._github_api_client = github_api_client

    def inspect(
        self,
        *,
        repository: str,
        workflow_path: str,
        workflow_ref: str,
        run_id: int | None,
        accessibility_job_name: str,
        axe_step_name: str,
        log_validation_step_name: str,
    ) -> GitHubWorkflowStepSequenceObservation:
        workflow_text = self._read_workflow_text(
            repository=repository,
            workflow_path=workflow_path,
            workflow_ref=workflow_ref,
        )
        workflow_jobs = self._workflow_jobs(workflow_text)
        workflow_job_id, workflow_job = self._find_workflow_job(
            workflow_jobs,
            expected_name=accessibility_job_name,
        )
        axe_step_contract = self._find_contract_step(
            job_id=workflow_job_id,
            job_name=accessibility_job_name if workflow_job is None else self._job_name(workflow_job_id, workflow_job),
            job_payload=workflow_job,
            step_name=axe_step_name,
        )
        log_validation_step_contract = self._find_contract_step(
            job_id=workflow_job_id,
            job_name=accessibility_job_name if workflow_job is None else self._job_name(workflow_job_id, workflow_job),
            job_payload=workflow_job,
            step_name=log_validation_step_name,
        )
        observed_job_names, observed_step_names, axe_step_run, log_validation_step_run = (
            self._read_run_step_sequence(
                repository=repository,
                run_id=run_id,
                accessibility_job_name=accessibility_job_name,
                axe_step_name=axe_step_name,
                log_validation_step_name=log_validation_step_name,
            )
        )

        return GitHubWorkflowStepSequenceObservation(
            repository=repository,
            workflow_path=workflow_path,
            workflow_ref=workflow_ref,
            workflow_url=f"https://github.com/{repository}/blob/{workflow_ref}/{workflow_path}",
            workflow_excerpt=self._workflow_excerpt(
                workflow_text,
                markers=[log_validation_step_name, axe_step_name],
            ),
            accessibility_job_name=(
                None
                if workflow_job is None
                else self._job_name(workflow_job_id, workflow_job)
            ),
            axe_step_contract=axe_step_contract,
            log_validation_step_contract=log_validation_step_contract,
            axe_step_run=axe_step_run,
            log_validation_step_run=log_validation_step_run,
            observed_job_names=observed_job_names,
            observed_step_names=observed_step_names,
        )

    def _read_workflow_text(
        self,
        *,
        repository: str,
        workflow_path: str,
        workflow_ref: str,
    ) -> str:
        payload = self._read_json_object(
            f"/repos/{repository}/contents/{workflow_path}?ref={workflow_ref}"
        )
        encoded = payload.get("content")
        if not isinstance(encoded, str) or not encoded.strip():
            raise GitHubWorkflowStepSequenceInspectorError(
                "GitHub workflow contents response did not include file content."
            )
        return base64.b64decode(encoded).decode("utf-8")

    def _workflow_jobs(self, workflow_text: str) -> dict[str, Any]:
        parsed = yaml.load(workflow_text, Loader=yaml.BaseLoader) or {}
        if not isinstance(parsed, dict):
            raise GitHubWorkflowStepSequenceInspectorError(
                "GitHub workflow YAML did not deserialize to a mapping."
            )
        jobs = parsed.get("jobs")
        if not isinstance(jobs, dict):
            return {}
        return jobs

    def _find_workflow_job(
        self,
        workflow_jobs: dict[str, Any],
        *,
        expected_name: str,
    ) -> tuple[str, dict[str, Any] | None]:
        normalized_expected = expected_name.strip().lower()
        for job_id, job_payload in workflow_jobs.items():
            if not isinstance(job_payload, dict):
                continue
            actual_name = self._job_name(str(job_id), job_payload)
            if actual_name.strip().lower() == normalized_expected:
                return str(job_id), job_payload
        return "", None

    def _find_contract_step(
        self,
        *,
        job_id: str,
        job_name: str,
        job_payload: dict[str, Any] | None,
        step_name: str,
    ) -> GitHubWorkflowStepContractObservation | None:
        if job_payload is None:
            return None
        steps = job_payload.get("steps")
        if not isinstance(steps, list):
            return None
        normalized_name = step_name.strip().lower()
        for step in steps:
            if not isinstance(step, dict):
                continue
            actual_name = self._optional_string(step.get("name"))
            if actual_name is None or actual_name.strip().lower() != normalized_name:
                continue
            if_condition = self._optional_string(step.get("if"))
            return GitHubWorkflowStepContractObservation(
                job_id=job_id,
                job_name=job_name,
                step_name=actual_name,
                if_condition=if_condition,
                uses_always=bool(
                    if_condition
                    and re.search(r"\balways\s*\(", if_condition, flags=re.IGNORECASE)
                ),
            )
        return None

    def _read_run_step_sequence(
        self,
        *,
        repository: str,
        run_id: int | None,
        accessibility_job_name: str,
        axe_step_name: str,
        log_validation_step_name: str,
    ) -> tuple[
        list[str],
        list[str],
        GitHubWorkflowRunStepObservation | None,
        GitHubWorkflowRunStepObservation | None,
    ]:
        if run_id is None:
            return [], [], None, None
        payload = self._read_json_object(
            f"/repos/{repository}/actions/runs/{run_id}/jobs?per_page=100"
        )
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise GitHubWorkflowStepSequenceInspectorError(
                f"GitHub Actions jobs response for run {run_id} did not return a jobs list."
            )

        observed_job_names: list[str] = []
        observed_step_names: list[str] = []
        accessibility_job: dict[str, Any] | None = None
        normalized_expected_job_name = accessibility_job_name.strip().lower()
        for job in jobs:
            if not isinstance(job, dict):
                continue
            job_name = self._optional_string(job.get("name"))
            if job_name:
                observed_job_names.append(job_name)
                if job_name.strip().lower() == normalized_expected_job_name:
                    accessibility_job = job
            steps = job.get("steps")
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                step_name = self._optional_string(step.get("name"))
                if step_name:
                    observed_step_names.append(step_name)

        if accessibility_job is None:
            return (
                self._dedupe(observed_job_names),
                self._dedupe(observed_step_names),
                None,
                None,
            )

        axe_step_run = self._find_run_step(accessibility_job, axe_step_name)
        log_validation_step_run = self._find_run_step(
            accessibility_job,
            log_validation_step_name,
        )
        return (
            self._dedupe(observed_job_names),
            self._dedupe(observed_step_names),
            axe_step_run,
            log_validation_step_run,
        )

    def _find_run_step(
        self,
        job_payload: dict[str, Any],
        step_name: str,
    ) -> GitHubWorkflowRunStepObservation | None:
        steps = job_payload.get("steps")
        if not isinstance(steps, list):
            return None
        normalized_name = step_name.strip().lower()
        job_name = self._optional_string(job_payload.get("name")) or ""
        for step in steps:
            if not isinstance(step, dict):
                continue
            actual_name = self._optional_string(step.get("name"))
            if actual_name is None or actual_name.strip().lower() != normalized_name:
                continue
            number = step.get("number")
            return GitHubWorkflowRunStepObservation(
                job_name=job_name,
                step_name=actual_name,
                number=number if isinstance(number, int) else None,
                status=self._optional_string(step.get("status")),
                conclusion=self._optional_string(step.get("conclusion")),
                started_at=self._optional_string(step.get("started_at")),
                completed_at=self._optional_string(step.get("completed_at")),
            )
        return None

    @staticmethod
    def _workflow_excerpt(workflow_text: str, *, markers: list[str]) -> str:
        lowered = workflow_text.lower()
        for marker in markers:
            index = lowered.find(marker.lower())
            if index >= 0:
                start = max(index - 250, 0)
                end = min(index + 900, len(workflow_text))
                return GitHubWorkflowStepSequenceInspectorService._snippet(
                    workflow_text[start:end],
                    limit=1400,
                )
        return GitHubWorkflowStepSequenceInspectorService._snippet(
            workflow_text,
            limit=1400,
        )

    @staticmethod
    def _snippet(text: str, *, limit: int) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3] + "..."

    @staticmethod
    def _job_name(job_id: str, payload: dict[str, Any]) -> str:
        name = payload.get("name")
        return str(name).strip() if isinstance(name, str) and name.strip() else job_id

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            if value and value not in result:
                result.append(value)
        return result

    def _read_json_object(self, endpoint: str) -> dict[str, Any]:
        try:
            payload = json.loads(self._github_api_client.request_text(endpoint=endpoint))
        except GitHubApiClientError as error:
            raise GitHubWorkflowStepSequenceInspectorError(str(error)) from error
        if not isinstance(payload, dict):
            raise GitHubWorkflowStepSequenceInspectorError(
                f"Expected a JSON object from gh api {endpoint}, got {type(payload)}."
            )
        return payload
