from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class AppleReleaseToolchainValidationStepObservation:
    name: str
    status: str | None
    conclusion: str | None
    number: int | None


@dataclass(frozen=True)
class AppleReleaseToolchainValidationJobObservation:
    name: str
    status: str | None
    conclusion: str | None
    url: str
    steps: list[AppleReleaseToolchainValidationStepObservation]


@dataclass(frozen=True)
class AppleReleaseToolchainValidationObservation:
    repository: str
    default_branch: str
    workflow_id: int
    workflow_name: str
    workflow_path: str
    workflow_url: str
    workflow_text: str
    main_ui_url: str | None
    main_ui_body_text: str
    main_ui_error: str | None
    main_ui_screenshot_path: str | None
    test_tag: str
    test_commit_sha: str
    run_id: int
    run_url: str
    run_event: str
    run_status: str | None
    run_conclusion: str | None
    run_created_at: str | None
    run_display_title: str | None
    jobs: list[AppleReleaseToolchainValidationJobObservation]
    verify_runner_job: AppleReleaseToolchainValidationJobObservation | None
    build_job: AppleReleaseToolchainValidationJobObservation | None
    setup_flutter_step: AppleReleaseToolchainValidationStepObservation | None
    validation_step: AppleReleaseToolchainValidationStepObservation | None
    desktop_build_step: AppleReleaseToolchainValidationStepObservation | None
    cli_build_step: AppleReleaseToolchainValidationStepObservation | None
    version_error_line: str | None
    run_log_excerpt: str
    cleanup_deleted_tag: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AppleReleaseToolchainValidationProbe(Protocol):
    def validate(self) -> AppleReleaseToolchainValidationObservation: ...
