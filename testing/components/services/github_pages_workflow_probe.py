from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request


class GitHubCliError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkflowStepObservation:
    name: str
    status: str | None
    conclusion: str | None


@dataclass(frozen=True)
class GitHubPagesWorkflowObservation:
    repository: str
    requested_repository: str
    workflow_file: str
    workflow_run_id: int
    workflow_run_url: str
    workflow_run_conclusion: str | None
    branch_sha_before: str
    branch_sha_after: str
    pages_url: str
    pages_build_type: str | None
    pages_source_branch: str | None
    pages_source_path: str | None
    html_title: str | None
    html_base_href: str | None
    html_contains_bootstrap_script: bool
    bootstrap_asset_url: str
    bootstrap_asset_mentions_main_dart_js: bool
    build_assets_committed_to_branch: list[str]
    required_step_names: list[str]
    observed_required_steps: list[str]
    missing_required_steps: list[str]
    failed_required_steps: list[str]
    selected_via_fallback: bool
    fallback_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GitHubPagesWorkflowProbe:
    _UPSTREAM_REPOSITORY = "IstiN/trackstate-setup"
    _WORKFLOW_FILE = "install-update-trackstate.yml"
    _WORKFLOW_REF = "main"
    _TRACKSTATE_REF = "main"
    _REQUIRED_STEPS = (
        "Build Flutter web app for this fork",
        "Upload Pages artifact",
        "Deploy to GitHub Pages",
    )
    _BUILD_ARTIFACT_PATTERNS = (
        re.compile(r"(^|/)index\.html$"),
        re.compile(r"(^|/)main\.dart\.js$"),
        re.compile(r"(^|/)flutter_bootstrap\.js$"),
        re.compile(r"(^|/)flutter_service_worker\.js$"),
        re.compile(r"(^|/)version\.json$"),
    )
    _HTML_TITLE_PATTERN = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
    _BASE_HREF_PATTERN = re.compile(r'<base href="([^"]+)">', re.IGNORECASE)
    _BOOTSTRAP_SCRIPT_PATTERN = re.compile(
        r'<script\s+src="flutter_bootstrap\.js"\s+async></script>',
        re.IGNORECASE,
    )

    def __init__(
        self,
        repository_root: Path,
        fork_registration_timeout_seconds: int = 120,
        run_timeout_seconds: int = 480,
        pages_timeout_seconds: int = 180,
        poll_interval_seconds: int = 5,
    ) -> None:
        self._repository_root = Path(repository_root)
        self._fork_registration_timeout_seconds = fork_registration_timeout_seconds
        self._run_timeout_seconds = run_timeout_seconds
        self._pages_timeout_seconds = pages_timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds

    def validate(self) -> GitHubPagesWorkflowObservation:
        requested_repository, selected_repository, fallback_reason = (
            self._select_repository_for_execution()
        )
        pages_info = self._ensure_pages_configuration(selected_repository)
        branch_sha_before = self._branch_sha(selected_repository)
        build_assets_committed = self._find_committed_build_assets(
            selected_repository,
            branch_sha_before,
        )
        runs_before_dispatch = {
            run["id"]
            for run in self._list_workflow_runs(selected_repository)
            if isinstance(run.get("id"), int)
        }

        self._dispatch_workflow(selected_repository)
        run = self._wait_for_new_workflow_run(
            selected_repository,
            runs_before_dispatch,
        )
        completed_run = self._wait_for_workflow_completion(
            selected_repository,
            int(run["id"]),
        )
        jobs = self._list_workflow_jobs(
            selected_repository,
            int(completed_run["id"]),
        )

        required_step_lookup: dict[str, WorkflowStepObservation] = {}
        for job in jobs:
            for step in job.get("steps", []):
                name = step.get("name")
                if name in self._REQUIRED_STEPS:
                    required_step_lookup[name] = WorkflowStepObservation(
                        name=name,
                        status=step.get("status"),
                        conclusion=step.get("conclusion"),
                    )

        missing_required_steps = [
            step_name
            for step_name in self._REQUIRED_STEPS
            if step_name not in required_step_lookup
        ]
        failed_required_steps = [
            step.name
            for step in required_step_lookup.values()
            if step.conclusion != "success"
        ]

        branch_sha_after = self._branch_sha(selected_repository)
        pages_info = self._ensure_pages_configuration(selected_repository)
        pages_url = str(pages_info["html_url"])
        html = self._wait_for_pages_shell(pages_url)
        bootstrap_asset_url = urllib_parse.urljoin(pages_url, "flutter_bootstrap.js")
        bootstrap_asset = self._read_url_text(bootstrap_asset_url)

        title_match = self._HTML_TITLE_PATTERN.search(html)
        base_href_match = self._BASE_HREF_PATTERN.search(html)

        return GitHubPagesWorkflowObservation(
            repository=selected_repository,
            requested_repository=requested_repository,
            workflow_file=self._WORKFLOW_FILE,
            workflow_run_id=int(completed_run["id"]),
            workflow_run_url=str(completed_run["html_url"]),
            workflow_run_conclusion=completed_run.get("conclusion"),
            branch_sha_before=branch_sha_before,
            branch_sha_after=branch_sha_after,
            pages_url=pages_url,
            pages_build_type=pages_info.get("build_type"),
            pages_source_branch=(pages_info.get("source") or {}).get("branch"),
            pages_source_path=(pages_info.get("source") or {}).get("path"),
            html_title=title_match.group(1).strip() if title_match else None,
            html_base_href=base_href_match.group(1).strip() if base_href_match else None,
            html_contains_bootstrap_script=bool(
                self._BOOTSTRAP_SCRIPT_PATTERN.search(html)
            ),
            bootstrap_asset_url=bootstrap_asset_url,
            bootstrap_asset_mentions_main_dart_js="main.dart.js" in bootstrap_asset,
            build_assets_committed_to_branch=build_assets_committed,
            required_step_names=list(self._REQUIRED_STEPS),
            observed_required_steps=list(required_step_lookup),
            missing_required_steps=missing_required_steps,
            failed_required_steps=failed_required_steps,
            selected_via_fallback=selected_repository != requested_repository,
            fallback_reason=fallback_reason,
        )

    def _select_repository_for_execution(self) -> tuple[str, str, str | None]:
        login = self._authenticated_login()
        requested_repository = (
            self._UPSTREAM_REPOSITORY
            if login == self._UPSTREAM_REPOSITORY.split("/")[0]
            else f"{login}/trackstate-setup"
        )

        if requested_repository == self._UPSTREAM_REPOSITORY:
            return requested_repository, requested_repository, None

        if not self._repository_exists(requested_repository):
            self._create_fork()

        if self._wait_for_repository(requested_repository):
            workflows = self._wait_for_workflow_registration(requested_repository)
            if workflows:
                return requested_repository, requested_repository, None

        fallback_reason = (
            "Fresh fork creation succeeded, but GitHub did not register the "
            "workflow in the fork within the wait window, so the live "
            "validation continued against the deployed upstream setup repository."
        )
        return requested_repository, self._UPSTREAM_REPOSITORY, fallback_reason

    def _authenticated_login(self) -> str:
        user = self._gh_json("user")
        login = user.get("login")
        if not isinstance(login, str) or not login:
            raise GitHubCliError("GitHub authentication did not return a valid login.")
        return login

    def _repository_exists(self, repository: str) -> bool:
        try:
            self._gh_json(f"repos/{repository}")
        except GitHubCliError as error:
            if "HTTP 404" in str(error):
                return False
            raise
        return True

    def _create_fork(self) -> None:
        self._gh_json(
            f"repos/{self._UPSTREAM_REPOSITORY}/forks",
            method="POST",
            field_args=["-f", "default_branch_only=true"],
        )

    def _wait_for_repository(self, repository: str) -> bool:
        deadline = time.time() + self._fork_registration_timeout_seconds
        while time.time() < deadline:
            if self._repository_exists(repository):
                return True
            time.sleep(self._poll_interval_seconds)
        return False

    def _wait_for_workflow_registration(self, repository: str) -> bool:
        deadline = time.time() + self._fork_registration_timeout_seconds
        while time.time() < deadline:
            workflows = self._gh_json(f"repos/{repository}/actions/workflows")
            for workflow in workflows.get("workflows", []):
                if workflow.get("path", "").endswith(self._WORKFLOW_FILE):
                    return True
            time.sleep(self._poll_interval_seconds)
        return False

    def _ensure_pages_configuration(self, repository: str) -> dict[str, Any]:
        pages_endpoint = f"repos/{repository}/pages"
        try:
            pages_info = self._gh_json(pages_endpoint)
        except GitHubCliError as error:
            if "HTTP 404" not in str(error):
                raise
            pages_info = self._gh_json(
                pages_endpoint,
                method="POST",
                stdin_json={
                    "build_type": "workflow",
                    "source": {"branch": self._WORKFLOW_REF, "path": "/"},
                },
            )

        if pages_info.get("build_type") != "workflow":
            pages_info = self._gh_json(
                pages_endpoint,
                method="PATCH",
                stdin_json={
                    "build_type": "workflow",
                    "source": {"branch": self._WORKFLOW_REF, "path": "/"},
                },
            )

        return pages_info

    def _dispatch_workflow(self, repository: str) -> None:
        self._gh_text(
            f"repos/{repository}/actions/workflows/{self._WORKFLOW_FILE}/dispatches",
            method="POST",
            field_args=[
                "-f",
                f"ref={self._WORKFLOW_REF}",
                "-F",
                f"inputs[trackstate_ref]={self._TRACKSTATE_REF}",
            ],
        )

    def _list_workflow_runs(self, repository: str) -> list[dict[str, Any]]:
        payload = self._gh_json(
            f"repos/{repository}/actions/workflows/{self._WORKFLOW_FILE}/runs"
            "?event=workflow_dispatch&per_page=20"
        )
        workflow_runs = payload.get("workflow_runs", [])
        if not isinstance(workflow_runs, list):
            raise GitHubCliError("GitHub Actions runs response was not a list.")
        return [
            run
            for run in workflow_runs
            if isinstance(run, dict) and run.get("event") == "workflow_dispatch"
        ]

    def _wait_for_new_workflow_run(
        self,
        repository: str,
        runs_before_dispatch: set[int],
    ) -> dict[str, Any]:
        deadline = time.time() + self._run_timeout_seconds
        while time.time() < deadline:
            runs = self._list_workflow_runs(repository)
            for run in runs:
                run_id = run.get("id")
                if isinstance(run_id, int) and run_id not in runs_before_dispatch:
                    return run
            time.sleep(self._poll_interval_seconds)
        raise GitHubCliError(
            f"No new workflow_dispatch run for {repository} appeared within "
            f"{self._run_timeout_seconds} seconds."
        )

    def _wait_for_workflow_completion(
        self,
        repository: str,
        run_id: int,
    ) -> dict[str, Any]:
        deadline = time.time() + self._run_timeout_seconds
        while time.time() < deadline:
            run = self._gh_json(f"repos/{repository}/actions/runs/{run_id}")
            if run.get("status") == "completed":
                return run
            time.sleep(self._poll_interval_seconds * 2)
        raise GitHubCliError(
            f"Workflow run {run_id} for {repository} did not complete within "
            f"{self._run_timeout_seconds} seconds."
        )

    def _list_workflow_jobs(self, repository: str, run_id: int) -> list[dict[str, Any]]:
        payload = self._gh_json(
            f"repos/{repository}/actions/runs/{run_id}/jobs?per_page=10"
        )
        jobs = payload.get("jobs", [])
        if not isinstance(jobs, list):
            raise GitHubCliError("GitHub Actions jobs response was not a list.")
        return [job for job in jobs if isinstance(job, dict)]

    def _branch_sha(self, repository: str, branch: str = "main") -> str:
        branch_info = self._gh_json(f"repos/{repository}/branches/{branch}")
        sha = ((branch_info.get("commit") or {}).get("sha"))
        if not isinstance(sha, str) or not sha:
            raise GitHubCliError(
                f"Repository {repository} branch {branch} did not return a commit SHA."
            )
        return sha

    def _find_committed_build_assets(
        self,
        repository: str,
        sha: str,
    ) -> list[str]:
        tree = self._gh_json(f"repos/{repository}/git/trees/{sha}?recursive=1")
        entries = tree.get("tree", [])
        if not isinstance(entries, list):
            raise GitHubCliError("Git tree response was not a list.")

        matched_paths: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("type") != "blob":
                continue
            path = entry.get("path")
            if not isinstance(path, str):
                continue
            if any(pattern.search(path) for pattern in self._BUILD_ARTIFACT_PATTERNS):
                matched_paths.append(path)
        return sorted(matched_paths)

    def _wait_for_pages_shell(self, pages_url: str) -> str:
        deadline = time.time() + self._pages_timeout_seconds
        last_html: str | None = None
        while time.time() < deadline:
            html = self._read_url_text(pages_url)
            last_html = html
            if (
                "TrackState.AI" in html
                and self._BOOTSTRAP_SCRIPT_PATTERN.search(html)
                and "GitHub Pages" not in html
                and "There isn't a GitHub Pages site here." not in html
            ):
                return html
            time.sleep(self._poll_interval_seconds * 2)

        raise GitHubCliError(
            "Timed out waiting for the GitHub Pages shell to serve the deployed "
            f"TrackState app at {pages_url}. Last HTML preview:\n"
            f"{(last_html or '')[:500]}"
        )

    def _read_url_text(self, url: str) -> str:
        request = urllib_request.Request(
            url,
            headers={
                "User-Agent": "trackstate-ts69-test",
                "Accept": "text/html,application/javascript;q=0.9,*/*;q=0.8",
            },
        )
        try:
            with urllib_request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
        except urllib_error.HTTPError as error:
            raise GitHubCliError(f"GET {url} failed with HTTP {error.code}.") from error
        except urllib_error.URLError as error:
            raise GitHubCliError(f"GET {url} failed: {error.reason}") from error
        return body

    def _gh_json(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
        stdin_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        stdout = self._gh_text(
            endpoint,
            method=method,
            field_args=field_args,
            stdin_json=stdin_json,
        )
        payload = json.loads(stdout or "{}")
        if not isinstance(payload, dict):
            raise GitHubCliError(
                f"Expected a JSON object from gh api {endpoint}, got {type(payload)}."
            )
        return payload

    def _gh_text(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
        stdin_json: dict[str, Any] | None = None,
    ) -> str:
        command = ["gh", "api", "-X", method, endpoint]
        if field_args:
            command.extend(field_args)
        input_text: str | None = None
        if stdin_json is not None:
            command.extend(["--input", "-"])
            input_text = json.dumps(stdin_json)

        environment = os.environ.copy()
        environment.setdefault("GH_PAGER", "cat")
        completed = subprocess.run(
            command,
            cwd=self._repository_root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            input=input_text,
        )
        if completed.returncode != 0:
            raise GitHubCliError(
                f"gh api {' '.join(command[2:])} failed with exit code "
                f"{completed.returncode}.\nSTDOUT:\n{completed.stdout}\nSTDERR:\n"
                f"{completed.stderr}"
            )
        return completed.stdout
