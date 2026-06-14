from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml
from yaml import Loader, SafeLoader

from testing.core.config.release_workflow_static_config import ReleaseWorkflowStaticConfig
from testing.core.interfaces.release_workflow_static_validator import (
    ReleaseWorkflowStaticObservation,
    ReleaseWorkflowStaticValidator,
)


class _WorkflowSafeLoader(SafeLoader):
    pass


# Prevent PyYAML from interpreting workflow keys such as 'on:' as booleans.
_WorkflowSafeLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:bool"]
    for key, resolvers in SafeLoader.yaml_implicit_resolvers.items()
}


class LocalReleaseWorkflowStaticValidator(ReleaseWorkflowStaticValidator):
    """Static validator for release workflow YAML and helper scripts."""

    def validate(self, config: ReleaseWorkflowStaticConfig) -> ReleaseWorkflowStaticObservation:
        failures: list[str] = []
        workflow_exists = config.workflow_path.exists()
        parsed: dict[str, Any] = {}
        triggers: list[str] = []
        jobs: dict[str, Any] = {}

        if not workflow_exists:
            failures.append(f"Workflow file not found: {config.workflow_path}")
            return ReleaseWorkflowStaticObservation(
                test_id=config.test_id,
                workflow_path=config.workflow_path,
                workflow_exists=False,
                failures=failures,
            )

        try:
            parsed = yaml.load(
                config.workflow_path.read_text(encoding="utf-8"),
                Loader=_WorkflowSafeLoader,
            ) or {}
        except yaml.YAMLError as exc:
            failures.append(f"Failed to parse workflow YAML: {exc}")
            return ReleaseWorkflowStaticObservation(
                test_id=config.test_id,
                workflow_path=config.workflow_path,
                workflow_exists=True,
                failures=failures,
            )

        if not isinstance(parsed, dict):
            failures.append("Workflow YAML root is not a mapping.")
            return ReleaseWorkflowStaticObservation(
                test_id=config.test_id,
                workflow_path=config.workflow_path,
                workflow_exists=True,
                failures=failures,
            )

        triggers = self._collect_triggers(parsed)
        jobs = parsed.get("jobs", {}) or {}
        if not isinstance(jobs, dict):
            failures.append("Workflow 'jobs' key is not a mapping.")
            jobs = {}

        failures.extend(self._check_triggers(config, triggers))
        failures.extend(self._check_jobs(config, jobs))
        failures.extend(self._check_job_dependencies(config, jobs))
        failures.extend(self._check_steps(config, jobs))
        failures.extend(self._check_uses(config, jobs))
        failures.extend(self._check_outputs(config, jobs))
        failures.extend(self._check_env_vars(config, parsed))
        failures.extend(self._check_markers(config, jobs))
        failures.extend(self._check_call_inputs(config, jobs))

        if config.script_tool_path:
            failures.extend(self._run_script_tool(config))

        return ReleaseWorkflowStaticObservation(
            test_id=config.test_id,
            workflow_path=config.workflow_path,
            workflow_exists=True,
            workflow_parsed=parsed,
            triggers=triggers,
            jobs=jobs,
            failures=failures,
        )

    def _collect_triggers(self, parsed: dict[str, Any]) -> list[str]:
        triggers = []
        for key in ("on", "true"):
            value = parsed.get(key)
            if value is not None:
                if isinstance(value, dict):
                    triggers.extend(value.keys())
                elif isinstance(value, list):
                    triggers.extend(value)
                elif isinstance(value, str):
                    triggers.append(value)
        return triggers

    def _check_triggers(
        self, config: ReleaseWorkflowStaticConfig, triggers: list[str]
    ) -> list[str]:
        failures = []
        for trigger in config.required_triggers:
            if trigger not in triggers:
                failures.append(
                    f"Required trigger '{trigger}' not found; observed triggers: {triggers}"
                )
        return failures

    def _check_jobs(
        self, config: ReleaseWorkflowStaticConfig, jobs: dict[str, Any]
    ) -> list[str]:
        failures = []
        job_names = set(jobs.keys())
        for required in config.required_jobs:
            if required not in job_names:
                failures.append(f"Required job '{required}' not found; jobs: {sorted(job_names)}")
        for forbidden in config.forbidden_jobs:
            if forbidden in job_names:
                failures.append(f"Forbidden job '{forbidden}' is present")
        return failures

    def _check_job_dependencies(
        self, config: ReleaseWorkflowStaticConfig, jobs: dict[str, Any]
    ) -> list[str]:
        failures = []
        for job_name, required_deps in config.required_job_dependencies.items():
            job = jobs.get(job_name)
            if not isinstance(job, dict):
                failures.append(f"Cannot check dependencies for missing job '{job_name}'")
                continue
            needs = job.get("needs")
            actual_deps: set[str] = set()
            if isinstance(needs, str):
                actual_deps.add(needs)
            elif isinstance(needs, list):
                actual_deps.update(str(item) for item in needs)
            for dep in required_deps:
                if dep not in actual_deps:
                    failures.append(
                        f"Job '{job_name}' missing required dependency '{dep}'; "
                        f"observed needs: {sorted(actual_deps)}"
                    )
        return failures

    def _check_steps(
        self, config: ReleaseWorkflowStaticConfig, jobs: dict[str, Any]
    ) -> list[str]:
        failures = []
        for job_name, required_markers in config.required_steps_by_job.items():
            job = jobs.get(job_name)
            if not isinstance(job, dict):
                failures.append(f"Cannot check steps for missing job '{job_name}'")
                continue
            steps = job.get("steps", []) or []
            step_names = [
                str(step.get("name", "")).lower()
                for step in steps
                if isinstance(step, dict)
            ]
            for marker in required_markers:
                if not any(marker.lower() in name for name in step_names):
                    failures.append(
                        f"Job '{job_name}' missing step matching marker '{marker}'; "
                        f"steps: {step_names}"
                    )
        return failures

    def _check_uses(
        self, config: ReleaseWorkflowStaticConfig, jobs: dict[str, Any]
    ) -> list[str]:
        failures = []
        for job_name, required_uses in config.required_uses_by_job.items():
            job = jobs.get(job_name)
            if not isinstance(job, dict):
                failures.append(f"Cannot check uses for missing job '{job_name}'")
                continue
            if "uses" in job:
                observed_uses = [job["uses"]]
            else:
                steps = job.get("steps", []) or []
                observed_uses = [
                    str(step.get("uses", ""))
                    for step in steps
                    if isinstance(step, dict)
                ]
            for required in required_uses:
                if not any(required in use for use in observed_uses):
                    failures.append(
                        f"Job '{job_name}' missing required reusable workflow reference "
                        f"'{required}'; observed: {observed_uses}"
                    )
        return failures

    def _check_outputs(
        self, config: ReleaseWorkflowStaticConfig, jobs: dict[str, Any]
    ) -> list[str]:
        failures = []
        for job_name, required_outputs in config.required_outputs_by_job.items():
            job = jobs.get(job_name)
            if not isinstance(job, dict):
                failures.append(f"Cannot check outputs for missing job '{job_name}'")
                continue
            outputs = job.get("outputs", {}) or {}
            if not isinstance(outputs, dict):
                failures.append(f"Job '{job_name}' outputs is not a mapping")
                continue
            for output in required_outputs:
                if output not in outputs:
                    failures.append(
                        f"Job '{job_name}' missing required output '{output}'; "
                        f"observed outputs: {sorted(outputs.keys())}"
                    )
        return failures

    def _check_env_vars(
        self, config: ReleaseWorkflowStaticConfig, parsed: dict[str, Any]
    ) -> list[str]:
        failures = []
        if not config.required_env_vars:
            return failures
        workflow_text = json.dumps(parsed)
        for env_var in config.required_env_vars:
            if env_var not in workflow_text:
                failures.append(f"Required environment variable/placeholder '{env_var}' not found")
        return failures

    def _check_markers(
        self, config: ReleaseWorkflowStaticConfig, jobs: dict[str, Any]
    ) -> list[str]:
        failures = []
        for job_name, markers in config.required_markers_in_job.items():
            job = jobs.get(job_name)
            if not isinstance(job, dict):
                failures.append(f"Cannot check markers for missing job '{job_name}'")
                continue
            job_text = json.dumps(job)
            for marker in markers:
                if marker not in job_text:
                    failures.append(
                        f"Job '{job_name}' missing required marker '{marker}'"
                    )
        return failures

    def _check_call_inputs(
        self, config: ReleaseWorkflowStaticConfig, jobs: dict[str, Any]
    ) -> list[str]:
        failures = []
        for job_name, expected_inputs in config.required_call_inputs.items():
            job = jobs.get(job_name)
            if not isinstance(job, dict):
                failures.append(f"Cannot check call inputs for missing job '{job_name}'")
                continue
            with_inputs = job.get("with", {})
            if not isinstance(with_inputs, dict):
                failures.append(f"Job '{job_name}' call inputs are not a mapping")
                continue
            for input_name, expected_value in expected_inputs.items():
                observed = with_inputs.get(input_name)
                if observed != expected_value:
                    failures.append(
                        f"Job '{job_name}' input '{input_name}' expected "
                        f"'{expected_value}', observed '{observed}'"
                    )
        return failures

    def _run_script_tool(
        self, config: ReleaseWorkflowStaticConfig
    ) -> list[str]:
        failures = []
        if not config.script_tool_path or not config.script_tool_path.exists():
            failures.append(f"Script tool not found: {config.script_tool_path}")
            return failures

        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                "CURRENT_SHA": "HEAD",
                "RELEASE_REF": "auto",
                "PATH": Path("/usr/bin:/bin"),
            }
            try:
                proc = subprocess.run(
                    ["bash", str(config.script_tool_path)] + config.script_args,
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=60,
                )
            except subprocess.TimeoutExpired:
                failures.append(f"Script tool timed out: {config.script_tool_path}")
                return failures
            except Exception as exc:
                failures.append(f"Script tool failed to execute: {exc}")
                return failures

            if proc.returncode != 0:
                failures.append(
                    f"Script tool exited {proc.returncode}: stdout={proc.stdout} stderr={proc.stderr}"
                )
                return failures

            outputs = {}
            for line in proc.stdout.splitlines():
                if "=" in line:
                    key, _, value = line.partition("=")
                    outputs[key.strip()] = value.strip()

            for key, expected in config.script_expected_outputs.items():
                observed = outputs.get(key)
                if observed is None:
                    failures.append(f"Script tool did not emit expected output '{key}'")
                    continue
                if not re.search(expected, observed):
                    failures.append(
                        f"Script output '{key}' value '{observed}' does not match pattern '{expected}'"
                    )

        return failures
