from __future__ import annotations

import json
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.tests.support.live_tracker_app_factory import (
    create_live_tracker_app_with_stored_token,
)


OUTPUTS_DIR = Path("outputs")
SCREENSHOT_PATH = OUTPUTS_DIR / "ts305_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    metadata = service.fetch_demo_metadata()
    user = service.fetch_authenticated_user()
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-305 requires GH_TOKEN or GITHUB_TOKEN to create an issue in the live app.",
        )

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    summary = f"TS-305 navigation verification {timestamp}"
    description = (
        "Automated live verification for post-create navigation. "
        f"Run timestamp: {timestamp}."
    )

    result: dict[str, object] = {
        "status": "failed",
        "ticket": "TS-305",
        "app_url": config.app_url,
        "repository": metadata.repository,
        "repository_ref": metadata.ref,
        "project_key": metadata.project_key,
        "user_login": user.login,
        "issue_summary": summary,
        "issue_description": description,
        "steps": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app showed a data-load failure before "
                        f"the Board workflow could be exercised. Observed text: {runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the live app and reach the tracker shell.",
                    observed=runtime.body_text,
                )

                connection = tracker_page.connect_with_token(
                    token=token,
                    repository=metadata.repository,
                    user_login=user.login,
                )
                result["connect_dialog_text"] = connection.dialog_text
                result["connected_body_text"] = connection.body_text
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Authenticate the live tracker with GitHub write access.",
                    observed=connection.body_text,
                )

                create_flow = tracker_page.create_issue_from_board(
                    summary=summary,
                    description=description,
                )
                result["board_text_before"] = create_flow.board_text_before
                result["create_dialog_text"] = create_flow.dialog_text
                result["detail_text"] = create_flow.detail_text
                result["board_text_after"] = create_flow.board_text_after
                result["created_issue_key"] = create_flow.created_issue_key
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Create a new issue from Board and wait for the post-save navigation.",
                    observed=create_flow.detail_text,
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Use Back to Board and verify the origin Board view refreshes with the new item.",
                    observed=create_flow.board_text_after,
                )
            except Exception:
                tracker_page.screenshot(str(SCREENSHOT_PATH))
                result["screenshot"] = str(SCREENSHOT_PATH)
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
            "Verified Board -> Create issue -> issue detail -> Back to Board on the "
            "live deployed tracker."
        )
        print(json.dumps(result, indent=2))


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


if __name__ == "__main__":
    main()
