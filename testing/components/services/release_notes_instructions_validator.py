from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from yaml import SafeLoader

from testing.core.config.release_notes_instructions_config import (
    ReleaseNotesInstructionsConfig,
)
from testing.core.interfaces.release_notes_instructions_validator import (
    ReleaseNotesInstructionsObservation,
    ReleaseNotesInstructionsValidator,
)


class _WorkflowSafeLoader(SafeLoader):
    pass


_WorkflowSafeLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:bool"]
    for key, resolvers in SafeLoader.yaml_implicit_resolvers.items()
}


class LocalReleaseNotesInstructionsValidator(ReleaseNotesInstructionsValidator):
    """Validates that release notes contain unsigned-package launch guidance
    under semantic Markdown headings.
    """

    def validate(
        self, config: ReleaseNotesInstructionsConfig
    ) -> ReleaseNotesInstructionsObservation:
        failures: list[str] = []
        workflow_exists = config.workflow_path.exists()
        publish_release_step_found = False
        release_notes_block_found = False
        unsigned_warning_present = False
        macos_guidance_present = False
        windows_guidance_present = False
        macos_guidance_has_heading = False
        windows_guidance_has_heading = False
        headings: list[str] = []

        if not workflow_exists:
            failures.append(f"Workflow file not found: {config.workflow_path}")
            return ReleaseNotesInstructionsObservation(
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
            return ReleaseNotesInstructionsObservation(
                test_id=config.test_id,
                workflow_path=config.workflow_path,
                workflow_exists=True,
                failures=failures,
            )

        if not isinstance(parsed, dict):
            failures.append("Workflow YAML root is not a mapping.")
            return ReleaseNotesInstructionsObservation(
                test_id=config.test_id,
                workflow_path=config.workflow_path,
                workflow_exists=True,
                failures=failures,
            )

        step_run = self._find_publish_release_run(parsed, config.publish_release_step_name)
        publish_release_step_found = step_run is not None
        if step_run is None:
            failures.append(
                f"Publish release step '{config.publish_release_step_name}' not found"
            )
        else:
            block = self._extract_appended_notes_block(step_run)
            release_notes_block_found = block is not None and bool(block.strip())
            if not release_notes_block_found:
                failures.append(
                    "Could not locate the appended release notes block "
                    "(expected '{ ... } >> \"$release_notes\"')."
                )
            else:
                assert block is not None
                reconstructed = self._reconstruct_markdown_lines(block)
                headings = [
                    line for line in reconstructed if re.match(config.heading_pattern, line)
                ]

                unsigned_warning_present = self._all_markers_present(
                    block, config.unsigned_warning_markers
                )
                macos_guidance_present = self._all_markers_present(
                    block, config.macos_guidance_markers
                )
                windows_guidance_present = self._all_markers_present(
                    block, config.windows_guidance_markers
                )

                macos_guidance_has_heading = self._guidance_preceded_by_heading(
                    reconstructed,
                    config.macos_guidance_markers,
                    config.heading_pattern,
                    config.heading_max_lines_before_guidance,
                )
                windows_guidance_has_heading = self._guidance_preceded_by_heading(
                    reconstructed,
                    config.windows_guidance_markers,
                    config.heading_pattern,
                    config.heading_max_lines_before_guidance,
                )

                if not unsigned_warning_present:
                    failures.append(
                        "Missing unsigned/unnotarized security warning in release notes."
                    )
                if not macos_guidance_present:
                    failures.append(
                        "Missing macOS launch guidance ('right-click' / 'Open')."
                    )
                if not windows_guidance_present:
                    failures.append(
                        "Missing Windows launch guidance ('More info' / 'Run anyway')."
                    )
                if macos_guidance_present and not macos_guidance_has_heading:
                    failures.append(
                        "macOS launch guidance is not introduced by an H2/H3 Markdown heading."
                    )
                if windows_guidance_present and not windows_guidance_has_heading:
                    failures.append(
                        "Windows launch guidance is not introduced by an H2/H3 Markdown heading."
                    )

        return ReleaseNotesInstructionsObservation(
            test_id=config.test_id,
            workflow_path=config.workflow_path,
            workflow_exists=workflow_exists,
            publish_release_step_found=publish_release_step_found,
            release_notes_block_found=release_notes_block_found,
            unsigned_warning_present=unsigned_warning_present,
            macos_guidance_present=macos_guidance_present,
            windows_guidance_present=windows_guidance_present,
            macos_guidance_has_heading=macos_guidance_has_heading,
            windows_guidance_has_heading=windows_guidance_has_heading,
            headings=headings,
            failures=failures,
        )

    def _find_publish_release_run(
        self, parsed: dict[str, Any], step_name: str
    ) -> str | None:
        jobs = parsed.get("jobs", {})
        if not isinstance(jobs, dict):
            return None
        for job in jobs.values():
            if not isinstance(job, dict):
                continue
            steps = job.get("steps", [])
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if str(step.get("name", "")).strip().lower() == step_name.strip().lower():
                    run = step.get("run")
                    if isinstance(run, str):
                        return run
        return None

    def _extract_appended_notes_block(self, run_script: str) -> str | None:
        # Capture the content of the brace block redirected into $release_notes.
        match = re.search(
            r"\{\s*(.*?)\s*\}\s*>>\s*\"?\$release_notes\"?",
            run_script,
            re.DOTALL,
        )
        if not match:
            return None
        return match.group(1)

    def _reconstruct_markdown_lines(self, block: str) -> list[str]:
        """Best-effort reconstruction of the rendered Markdown from echo lines."""
        lines: list[str] = []
        for raw_line in block.splitlines():
            line = raw_line.strip()
            # Strip leading echo and surrounding quotes.
            if line.startswith("echo "):
                line = line[len("echo "):].strip()
            if len(line) >= 2 and line[0] == line[-1] == '"':
                line = line[1:-1]
            lines.append(line)
        return lines

    def _all_markers_present(self, text: str, markers: list[str]) -> bool:
        lowered = text.lower()
        return all(marker.lower() in lowered for marker in markers)

    def _guidance_preceded_by_heading(
        self,
        lines: list[str],
        markers: list[str],
        heading_pattern: str,
        max_lines: int,
    ) -> bool:
        lowered_markers = [m.lower() for m in markers]
        for idx, line in enumerate(lines):
            lowered = line.lower()
            if all(marker in lowered for marker in lowered_markers):
                # Search backwards for a heading within the allowed window.
                start = max(0, idx - max_lines)
                for previous in lines[start:idx]:
                    if re.match(heading_pattern, previous):
                        return True
        return False
