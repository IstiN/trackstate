from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlparse

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class PullRequestTemplateCandidateObservation:
    path: str
    contents_fetch: CliCommandResult
    raw_fetch: CliCommandResult

    @property
    def exists(self) -> bool:
        return self.contents_fetch.succeeded or self.raw_fetch.succeeded

    @property
    def entry_type(self) -> str | None:
        payload = self.contents_fetch.json_payload
        if isinstance(payload, dict):
            entry_type = payload.get("type")
            if isinstance(entry_type, str) and entry_type:
                return entry_type
        return None

    @property
    def raw_text(self) -> str | None:
        if self.raw_fetch.succeeded:
            return self.raw_fetch.stdout
        payload = self.contents_fetch.json_payload
        if isinstance(payload, dict):
            content = payload.get("content")
            encoding = payload.get("encoding")
            if (
                isinstance(content, str)
                and content
                and isinstance(encoding, str)
                and encoding == "base64"
            ):
                return CliCommandResult.decode_base64_text(content)
        return None


@dataclass(frozen=True)
class RecognizedPullRequestTemplate:
    filename: str
    body: str


@dataclass(frozen=True)
class PullRequestTemplateChecklistVerificationResult:
    target_repository: str
    required_checklist_item: str
    repository_info: CliCommandResult
    community_profile: CliCommandResult
    tree_fetch: CliCommandResult
    pull_request_templates_fetch: CliCommandResult
    candidate_observations: tuple[PullRequestTemplateCandidateObservation, ...]

    @property
    def repository_metadata(self) -> dict[str, object]:
        payload = self.repository_info.json_payload
        return payload if isinstance(payload, dict) else {}

    @property
    def default_branch(self) -> str | None:
        default_branch = self.repository_metadata.get("default_branch")
        if isinstance(default_branch, str) and default_branch:
            return default_branch
        return None

    @property
    def community_profile_payload(self) -> dict[str, object]:
        payload = self.community_profile.json_payload
        return payload if isinstance(payload, dict) else {}

    @property
    def configured_pull_request_template_url(self) -> str | None:
        files = self.community_profile_payload.get("files")
        if not isinstance(files, dict):
            return None
        template = files.get("pull_request_template")
        if not isinstance(template, dict):
            return None
        html_url = template.get("html_url")
        if isinstance(html_url, str) and html_url:
            return html_url
        return None

    @property
    def configured_pull_request_template_path(self) -> str | None:
        html_url = self.configured_pull_request_template_url
        if not html_url:
            return None
        parsed = urlparse(html_url)
        prefix = f"/{self.target_repository}/blob/"
        if not parsed.path.startswith(prefix):
            return None
        remainder = parsed.path[len(prefix) :]
        branch_separator = remainder.find("/")
        if branch_separator == -1:
            return None
        path = remainder[branch_separator + 1 :]
        return path if path else None

    @property
    def tree_paths(self) -> tuple[str, ...]:
        payload = self.tree_fetch.json_payload
        if not isinstance(payload, dict):
            return ()
        tree = payload.get("tree")
        if not isinstance(tree, list):
            return ()
        paths: list[str] = []
        for item in tree:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            if isinstance(path, str) and path:
                paths.append(path)
        return tuple(paths)

    @property
    def discovered_template_paths(self) -> tuple[str, ...]:
        pattern = re.compile(
            r"(?i)(^|/)(pull_request_template(\.md)?|pull_request_template/[^/]+\.md)$"
        )
        return tuple(path for path in self.tree_paths if pattern.search(path))

    @property
    def recognized_templates(self) -> tuple[RecognizedPullRequestTemplate, ...]:
        payload = self.pull_request_templates_fetch.json_payload
        if not isinstance(payload, dict):
            return ()
        data = payload.get("data")
        if not isinstance(data, dict):
            return ()
        repository = data.get("repository")
        if not isinstance(repository, dict):
            return ()
        templates = repository.get("pullRequestTemplates")
        if not isinstance(templates, list):
            return ()
        recognized_templates: list[RecognizedPullRequestTemplate] = []
        for template in templates:
            if not isinstance(template, dict):
                continue
            filename = template.get("filename")
            body = template.get("body")
            if isinstance(filename, str) and filename and isinstance(body, str):
                recognized_templates.append(
                    RecognizedPullRequestTemplate(filename=filename, body=body)
                )
        return tuple(recognized_templates)

    @property
    def existing_candidates(self) -> tuple[PullRequestTemplateCandidateObservation, ...]:
        return tuple(
            observation
            for observation in self.candidate_observations
            if observation.exists and observation.entry_type in {None, "file"}
        )

    @property
    def selected_candidate(self) -> PullRequestTemplateCandidateObservation | None:
        configured_path = self.configured_pull_request_template_path
        if configured_path is not None:
            for observation in self.existing_candidates:
                if observation.path == configured_path:
                    return observation
        return self.existing_candidates[0] if self.existing_candidates else None

    @property
    def selected_recognized_template(self) -> RecognizedPullRequestTemplate | None:
        configured_path = self.configured_pull_request_template_path
        if configured_path is not None:
            for template in self.recognized_templates:
                if template.filename == configured_path:
                    return template
        selected_candidate = self.selected_candidate
        if selected_candidate is not None:
            for template in self.recognized_templates:
                if template.filename == selected_candidate.path:
                    return template
        return self.recognized_templates[0] if self.recognized_templates else None
