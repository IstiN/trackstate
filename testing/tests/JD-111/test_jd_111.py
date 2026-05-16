from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.jd_111_index_page import JD111IndexPage
from testing.core.config.jd_111_index_page_config import load_jd_111_index_page_config
from testing.frameworks.python.playwright_web_app_session import PlaywrightWebAppRuntime

TICKET_KEY = "JD-111"
OUTPUTS_DIR = REPO_ROOT / "outputs"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "jd_111_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "jd_111_success.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_jd_111_index_page_config()
    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "index_url": config.index_url,
        "expected_sections": list(config.expected_sections),
        "expected_feature_card_count": config.expected_feature_card_count,
        "expected_workflow_step_count": config.expected_workflow_step_count,
        "steps": [],
    }

    try:
        with PlaywrightWebAppRuntime() as session:
            page = JD111IndexPage(session, config.index_url)
            try:
                page.open()
                observation = page.observe()
                result["observation"] = _observation_to_dict(observation)

                _assert_page_loaded(observation)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Navigate to the project's index.html page.",
                    observed=(
                        f"Loaded {observation.url}\n"
                        f"Document title: {observation.title}\n"
                        f"Visible body text: {observation.body_text or '[empty]'}"
                    ),
                )

                _assert_project_information_section(
                    observation=observation,
                    expected_sections=config.expected_sections,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Identify the section containing project information.",
                    observed=(
                        "Visible headings: "
                        + (", ".join(observation.headings) if observation.headings else "[none]")
                    ),
                )

                _assert_extended_details(
                    observation=observation,
                    expected_sections=config.expected_sections,
                    expected_feature_card_count=config.expected_feature_card_count,
                    expected_workflow_step_count=config.expected_workflow_step_count,
                )
                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Verify the additional project details are displayed as intended.",
                    observed=(
                        f"Feature cards: {observation.feature_card_count}\n"
                        f"Workflow steps: {observation.workflow_step_count}\n"
                        f"Tech tags: {observation.tech_tag_count}\n"
                        f"Visible headings: {', '.join(observation.headings)}"
                    ),
                )
            except Exception:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        print(json.dumps(result, indent=2))
        raise
    else:
        result["status"] = "passed"
        result["summary"] = (
            "Verified that web/index.html loads and visibly renders the extended "
            "project information sections for JD-111."
        )
        print(json.dumps(result, indent=2))


def _assert_page_loaded(observation) -> None:
    if not observation.title.strip():
        raise AssertionError(
            "Step 1 failed: the index.html page loaded without a document title.\n"
            f"Observed URL: {observation.url}\n"
            f"Visible body text: {observation.body_text or '[empty]'}\n"
            f"HTML excerpt:\n{observation.html_excerpt or '[empty]'}",
        )


def _assert_project_information_section(
    *,
    observation,
    expected_sections: tuple[str, ...],
) -> None:
    visible_sections = [section for section in expected_sections if section in observation.body_text]
    if visible_sections:
        return
    raise AssertionError(
        "Step 2 failed: the index.html page did not show any visible extended project "
        "information section.\n"
        f"Expected one of: {list(expected_sections)}\n"
        f"Observed headings: {list(observation.headings)}\n"
        f"Visible body text: {observation.body_text or '[empty]'}\n"
        f"HTML excerpt:\n{observation.html_excerpt or '[empty]'}",
    )


def _assert_extended_details(
    *,
    observation,
    expected_sections: tuple[str, ...],
    expected_feature_card_count: int,
    expected_workflow_step_count: int,
) -> None:
    missing_sections = [
        section for section in expected_sections if section not in observation.body_text
    ]
    if missing_sections:
        raise AssertionError(
            "Step 3 failed: the page did not render all expected extended project "
            "information sections.\n"
            f"Missing sections: {missing_sections}\n"
            f"Observed headings: {list(observation.headings)}\n"
            f"Visible body text: {observation.body_text or '[empty]'}",
        )
    if observation.feature_card_count != expected_feature_card_count:
        raise AssertionError(
            "Step 3 failed: the Key Features section did not render the expected number "
            "of feature cards.\n"
            f"Expected feature card count: {expected_feature_card_count}\n"
            f"Observed feature card count: {observation.feature_card_count}\n"
            f"Visible body text: {observation.body_text or '[empty]'}",
        )
    if observation.workflow_step_count != expected_workflow_step_count:
        raise AssertionError(
            "Step 3 failed: the AI Automation Workflow section did not render the expected "
            "number of workflow steps.\n"
            f"Expected workflow step count: {expected_workflow_step_count}\n"
            f"Observed workflow step count: {observation.workflow_step_count}\n"
            f"Visible body text: {observation.body_text or '[empty]'}",
        )
    if observation.tech_tag_count <= 0:
        raise AssertionError(
            "Human-style verification failed: the page did not show any visible Tech Stack "
            "tags to the user.\n"
            f"Visible body text: {observation.body_text or '[empty]'}",
        )


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    assert isinstance(steps, list)
    steps.append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        },
    )


def _observation_to_dict(observation) -> dict[str, object]:
    return {
        "url": observation.url,
        "title": observation.title,
        "body_text": observation.body_text,
        "headings": list(observation.headings),
        "feature_card_count": observation.feature_card_count,
        "workflow_step_count": observation.workflow_step_count,
        "tech_tag_count": observation.tech_tag_count,
        "html_excerpt": observation.html_excerpt,
    }


if __name__ == "__main__":
    main()
