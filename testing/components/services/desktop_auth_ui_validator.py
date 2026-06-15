from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from yaml import SafeLoader

from testing.core.config.desktop_auth_ui_config import DesktopAuthUIConfig
from testing.core.interfaces.desktop_auth_ui_validator import (
    DesktopAuthUIObservation,
    DesktopAuthUIValidator,
)


class _WorkflowSafeLoader(SafeLoader):
    pass


_WorkflowSafeLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:bool"]
    for key, resolvers in SafeLoader.yaml_implicit_resolvers.items()
}


class LocalDesktopAuthUIValidator(DesktopAuthUIValidator):
    """Validates that desktop builds keep GitHub App OAuth out of the auth UI."""

    def validate(self, config: DesktopAuthUIConfig) -> DesktopAuthUIObservation:
        failures: list[str] = []
        workflow_exists = config.workflow_path.exists()
        desktop_jobs_found: list[str] = []
        desktop_jobs_without_oauth: list[str] = []
        desktop_jobs_with_oauth: list[str] = []
        web_step_has_oauth = False
        auth_source_exists = False
        github_app_button_conditional = False
        unconditional_github_app_button = True
        pat_input_present = False
        connect_token_button_present = False
        labels_present: list[str] = []
        labels_missing: list[str] = []

        if not workflow_exists:
            failures.append(f"Workflow file not found: {config.workflow_path}")
            return DesktopAuthUIObservation(
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
            return DesktopAuthUIObservation(
                test_id=config.test_id,
                workflow_path=config.workflow_path,
                workflow_exists=True,
                failures=failures,
            )

        if not isinstance(parsed, dict):
            failures.append("Workflow YAML root is not a mapping.")
            return DesktopAuthUIObservation(
                test_id=config.test_id,
                workflow_path=config.workflow_path,
                workflow_exists=True,
                failures=failures,
            )

        jobs = parsed.get("jobs", {})
        if isinstance(jobs, dict):
            for job_name in config.desktop_build_job_names:
                job = jobs.get(job_name)
                if not isinstance(job, dict):
                    continue
                desktop_jobs_found.append(job_name)
                job_text = json.dumps(job)
                has_oauth = any(marker in job_text for marker in config.oauth_dart_defines)
                if has_oauth:
                    desktop_jobs_with_oauth.append(job_name)
                else:
                    desktop_jobs_without_oauth.append(job_name)

            web_step_has_oauth = self._web_step_has_oauth(
                jobs, config.web_build_step_name, config.oauth_dart_defines
            )

        auth_source_path = config.repository_root / config.auth_source_relative_path
        auth_source_exists = auth_source_path.exists()
        if not auth_source_exists:
            failures.append(f"Auth source file not found: {auth_source_path}")
        else:
            source_text = auth_source_path.read_text(encoding="utf-8")
            github_app_button_conditional = self._is_conditional_button(
                source_text, config.conditional_flag, config.github_app_button_label_key
            )
            unconditional_github_app_button = self._has_unconditional_button(
                source_text, config.conditional_flag, config.github_app_button_label_key
            )
            pat_input_present = self._has_pat_input(source_text, config.pat_input_label_key)
            connect_token_button_present = self._has_connect_button(
                source_text, config.connect_button_label_key
            )

        l10n_path = config.repository_root / config.localization_file_relative_path
        if not l10n_path.exists():
            failures.append(f"Localization file not found: {l10n_path}")
        else:
            l10n_text = l10n_path.read_text(encoding="utf-8")
            for key in config.required_label_keys:
                if self._has_non_empty_l10n_value(l10n_text, key):
                    labels_present.append(key)
                else:
                    labels_missing.append(key)

        if desktop_jobs_with_oauth:
            failures.append(
                "Desktop build jobs must not pass GitHub App OAuth dart-defines: "
                + ", ".join(desktop_jobs_with_oauth)
            )
        if not web_step_has_oauth:
            failures.append(
                "Web build step should pass GitHub App OAuth dart-defines "
                "to confirm the scope distinction."
            )
        if not auth_source_exists:
            pass  # already recorded
        else:
            if not github_app_button_conditional:
                failures.append(
                    "Auth dialog does not conditionally render the GitHub App button "
                    "based on the configured flag."
                )
            if unconditional_github_app_button:
                failures.append(
                    "Auth dialog contains an unconditional 'Continue with GitHub App' button."
                )
            if not pat_input_present:
                failures.append(
                    "Auth dialog is missing the Personal Access Token input field."
                )
            if not connect_token_button_present:
                failures.append(
                    "Auth dialog is missing the token-connect submit button."
                )
        if labels_missing:
            failures.append(
                "Missing or empty Semantics-visible labels for auth controls: "
                + ", ".join(labels_missing)
            )

        return DesktopAuthUIObservation(
            test_id=config.test_id,
            workflow_path=config.workflow_path,
            workflow_exists=workflow_exists,
            desktop_jobs_found=desktop_jobs_found,
            desktop_jobs_without_oauth=desktop_jobs_without_oauth,
            desktop_jobs_with_oauth=desktop_jobs_with_oauth,
            web_step_has_oauth=web_step_has_oauth,
            auth_source_exists=auth_source_exists,
            github_app_button_conditional=github_app_button_conditional,
            unconditional_github_app_button=unconditional_github_app_button,
            pat_input_present=pat_input_present,
            connect_token_button_present=connect_token_button_present,
            labels_present=labels_present,
            labels_missing=labels_missing,
            failures=failures,
        )

    def _web_step_has_oauth(
        self,
        jobs: dict[str, Any],
        step_name: str,
        oauth_dart_defines: list[str],
    ) -> bool:
        for job in jobs.values():
            if not isinstance(job, dict):
                continue
            steps = job.get("steps", [])
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if str(step.get("name", "")).strip() != step_name:
                    continue
                step_text = json.dumps(step)
                return all(marker in step_text for marker in oauth_dart_defines)
        return False

    def _is_conditional_button(
        self, source_text: str, conditional_flag: str, label_key: str
    ) -> bool:
        # The label key should appear after the conditional flag within a reasonable window.
        flag_match = re.search(re.escape(conditional_flag), source_text)
        if not flag_match:
            return False
        window = source_text[flag_match.start():flag_match.start() + 800]
        return f"l10n.{label_key}" in window

    def _has_unconditional_button(
        self, source_text: str, conditional_flag: str, label_key: str
    ) -> bool:
        # Find occurrences of the button label that are NOT inside the conditional block.
        flag_match = re.search(re.escape(conditional_flag), source_text)
        if not flag_match:
            # Without the flag, any occurrence is effectively unconditional for this test.
            return f"l10n.{label_key}" in source_text
        before_flag = source_text[: flag_match.start()]
        return f"l10n.{label_key}" in before_flag

    def _has_pat_input(self, source_text: str, label_key: str) -> bool:
        return f"labelText: l10n.{label_key}" in source_text

    def _has_connect_button(self, source_text: str, label_key: str) -> bool:
        return f"l10n.{label_key}" in source_text

    def _has_non_empty_l10n_value(self, l10n_text: str, key: str) -> bool:
        # Simple JSON value extraction; app_en.arb values are quoted strings.
        match = re.search(
            rf'"{re.escape(key)}"\s*:\s*"(.*?)"',
            l10n_text,
            re.DOTALL,
        )
        if not match:
            return False
        value = match.group(1).strip()
        return bool(value)
