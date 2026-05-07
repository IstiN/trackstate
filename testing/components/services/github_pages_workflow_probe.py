from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib import parse as urllib_parse

from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)
from testing.core.interfaces.github_pages_workflow_probe import (
    GitHubPagesWorkflowObservation,
)
from testing.core.interfaces.url_text_reader import UrlTextReader, UrlTextReaderError
from testing.core.models.github_pages_workflow_probe_config import (
    GitHubPagesWorkflowProbeConfig,
)


class GitHubCliError(RuntimeError):
    pass


class GitHubPagesWorkflowProbe:
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
        config: GitHubPagesWorkflowProbeConfig,
        github_api_client: GitHubApiClient,
        url_text_reader: UrlTextReader,
        fork_registration_timeout_seconds: int = 300,
        run_timeout_seconds: int = 480,
        pages_timeout_seconds: int = 180,
        poll_interval_seconds: int = 5,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client
        self._url_text_reader = url_text_reader
        self._fork_registration_timeout_seconds = fork_registration_timeout_seconds
        self._run_timeout_seconds = run_timeout_seconds
        self._pages_timeout_seconds = pages_timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds

    def validate(self) -> GitHubPagesWorkflowObservation:
        requested_repository = self._select_repository_for_execution()
        expected_pages_url = self._expected_pages_url(requested_repository)
        pages_info = self._ensure_pages_configuration(requested_repository)
        branch_sha_before = self._branch_sha(requested_repository)
        build_assets_committed = self._find_committed_build_assets(
            requested_repository,
            branch_sha_before,
        )
        runs_before_dispatch = {
            run["id"]
            for run in self._list_workflow_runs(requested_repository)
            if isinstance(run.get("id"), int)
        }

        self._dispatch_workflow(requested_repository)
        run = self._wait_for_new_workflow_run(
            requested_repository,
            runs_before_dispatch,
        )
        completed_run = self._wait_for_workflow_completion(
            requested_repository,
            int(run["id"]),
        )
        jobs = self._list_workflow_jobs(
            requested_repository,
            int(completed_run["id"]),
        )

        required_step_lookup: dict[str, dict[str, str | None]] = {}
        for job in jobs:
            for step in job.get("steps", []):
                name = step.get("name")
                if name in self._REQUIRED_STEPS:
                    required_step_lookup[name] = {
                        "status": step.get("status"),
                        "conclusion": step.get("conclusion"),
                    }

        missing_required_steps = [
            step_name
            for step_name in self._REQUIRED_STEPS
            if step_name not in required_step_lookup
        ]
        failed_required_steps = [
            step_name
            for step_name, step in required_step_lookup.items()
            if step.get("conclusion") != "success"
        ]

        branch_sha_after = self._branch_sha(requested_repository)
        pages_info = self._ensure_pages_configuration(requested_repository)
        pages_url = self._normalize_pages_url(str(pages_info["html_url"]))
        html = self._wait_for_pages_shell(pages_url)
        bootstrap_asset_url = urllib_parse.urljoin(pages_url, "flutter_bootstrap.js")
        bootstrap_asset = self._read_url_text(bootstrap_asset_url)

        title_match = self._HTML_TITLE_PATTERN.search(html)
        base_href_match = self._BASE_HREF_PATTERN.search(html)

        return GitHubPagesWorkflowObservation(
            repository=requested_repository,
            requested_repository=requested_repository,
            expected_pages_url=expected_pages_url,
            workflow_file=self._config.workflow_file,
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
        )

    def _select_repository_for_execution(self) -> str:
        login = self._authenticated_login()
        upstream_repository = self._config.upstream_repository
        try:
            requested_repository = self._config.requested_repository_for(login)
        except ValueError as error:
            raise GitHubCliError(str(error)) from error

        if not self._repository_exists(requested_repository):
            self._create_fork()

        if not self._wait_for_repository(requested_repository):
            raise GitHubCliError(
                "TS-69 requires validating the requested fork, but "
                f"{requested_repository} did not become available within "
                f"{self._fork_registration_timeout_seconds} seconds."
            )

        if not self._wait_for_workflow_registration(requested_repository):
            raise GitHubCliError(
                "TS-69 requires validating the requested fork, but GitHub did not "
                f"register {self._config.workflow_file} for {requested_repository} "
                "within "
                f"{self._fork_registration_timeout_seconds} seconds. The probe does "
                f"not fall back to {upstream_repository}."
            )

        return requested_repository

    def _expected_pages_url(self, repository: str) -> str:
        owner, repo = repository.split("/", 1)
        return self._normalize_pages_url(f"https://{owner}.github.io/{repo}/")

    def _normalize_pages_url(self, url: str) -> str:
        parsed = urllib_parse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise GitHubCliError(f"GitHub Pages URL was not absolute: {url}")
        normalized_path = parsed.path or "/"
        if not normalized_path.endswith("/"):
            normalized_path = f"{normalized_path}/"
        return urllib_parse.urlunparse(
            parsed._replace(netloc=parsed.netloc.lower(), path=normalized_path)
        )

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
            f"repos/{self._config.upstream_repository}/forks",
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
                if workflow.get("path", "").endswith(self._config.workflow_file):
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
                    "source": {"branch": self._config.workflow_ref, "path": "/"},
                },
            )

        if pages_info.get("build_type") != "workflow":
            pages_info = self._gh_json(
                pages_endpoint,
                method="PATCH",
                stdin_json={
                    "build_type": "workflow",
                    "source": {"branch": self._config.workflow_ref, "path": "/"},
                },
            )

        return pages_info

    def _dispatch_workflow(self, repository: str) -> None:
        self._gh_text(
            f"repos/{repository}/actions/workflows/{self._config.workflow_file}/dispatches",
            method="POST",
            field_args=[
                "-f",
                f"ref={self._config.workflow_ref}",
                "-F",
                f"inputs[trackstate_ref]={self._config.trackstate_ref}",
            ],
        )

    def _list_workflow_runs(self, repository: str) -> list[dict[str, Any]]:
        payload = self._gh_json(
            f"repos/{repository}/actions/workflows/{self._config.workflow_file}/runs"
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
        try:
            return self._url_text_reader.read_text(
                url=url,
                headers={
                    "User-Agent": "trackstate-ts69-test",
                    "Accept": "text/html,application/javascript;q=0.9,*/*;q=0.8",
                },
                timeout_seconds=30,
            )
        except UrlTextReaderError as error:
            raise GitHubCliError(str(error)) from error

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
        try:
            return self._github_api_client.request_text(
                endpoint=endpoint,
                method=method,
                field_args=field_args,
                stdin_json=stdin_json,
            )
        except GitHubApiClientError as error:
            raise GitHubCliError(str(error)) from error
