from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.trackstate_live_app_page import TrackStateLiveAppPage
from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)


APP_URL = "https://istin.github.io/trackstate-setup/"
OUTPUTS_DIR = Path("outputs")
SCREENSHOT_PATH = OUTPUTS_DIR / "ts70_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    service = LiveSetupRepositoryService()
    metadata = service.fetch_demo_metadata()
    user = service.fetch_authenticated_user()
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-70 requires GH_TOKEN or GITHUB_TOKEN to drive the live PAT login flow.",
        )

    result: dict[str, object] = {
        "status": "failed",
        "app_url": APP_URL,
        "repository": metadata.repository,
        "repository_ref": metadata.ref,
        "expected_issue_types": metadata.issue_types,
        "expected_statuses": metadata.statuses,
        "expected_fields": metadata.fields,
        "user_login": user.login,
    }

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 960})

            def add_github_auth(route) -> None:
                headers = dict(route.request.headers)
                headers["authorization"] = f"Bearer {token}"
                headers["accept"] = "application/vnd.github+json"
                headers["x-github-api-version"] = "2022-11-28"
                route.continue_(headers=headers)

            context.route("https://api.github.com/**", add_github_auth)
            page = context.new_page()
            live_page = TrackStateLiveAppPage(page, APP_URL)

            live_page.open()
            state = live_page.wait_for_runtime_state()
            result["runtime_state"] = state.kind
            result["body_text"] = state.body_text

            if state.kind == "data-load-failed":
                live_page.screenshot(str(SCREENSHOT_PATH))
                raise AssertionError(
                    "Step 1 failed: the deployed app did not reach the Connect GitHub state. "
                    f"Observed load error instead: {state.body_text}"
                )
            if state.kind == "timeout":
                live_page.screenshot(str(SCREENSHOT_PATH))
                raise AssertionError(
                    "Step 1 failed: the deployed app never exposed Connect GitHub or a final error state "
                    f"within the wait window. Visible body text: {state.body_text}"
                )

            if "Connect GitHub" not in state.body_text:
                raise AssertionError(
                    "Step 1 failed: the deployed app loaded, but the Connect GitHub control was not visible.",
                )

            live_page.open_connect_dialog()
            dialog_text = live_page.body_text()
            result["dialog_text"] = dialog_text
            for expected_text in [
                f"Repository: {metadata.repository}",
                "Needs Contents: read/write. Stored only on this device if remembered.",
                "Connect token",
            ]:
                if expected_text not in dialog_text:
                    raise AssertionError(
                        f'Step 2 failed: missing dialog text "{expected_text}". '
                        f"Observed dialog/body text: {dialog_text}"
                    )
            if page.locator('input[aria-label="Fine-grained token"]').count() != 1:
                raise AssertionError(
                    "Step 2 failed: the Connect GitHub dialog did not expose exactly one Fine-grained token input.",
                )
            if (
                page.locator(
                    'flt-semantics[role="checkbox"][aria-label*="Remember on this browser"]',
                ).count()
                != 1
            ):
                raise AssertionError(
                    "Step 2 failed: the Connect GitHub dialog did not expose the Remember on this browser option.",
                )

            live_page.fill_fine_grained_token(token)
            live_page.submit_connect_token()

            connected_banner = (
                f"Connected as {user.login} to {metadata.repository}. "
                "Drag cards to commit status changes."
            )
            after_connect = live_page.wait_for_body_text(connected_banner)
            result["after_connect_text"] = after_connect
            if "Connected" not in after_connect:
                raise AssertionError(
                    "Step 4 failed: the repository access control never changed to Connected.",
                )

            live_page.open_settings()
            settings_text = live_page.wait_for_body_text("Project Settings")
            result["settings_text"] = settings_text
            for expected_text in [
                "Project Settings",
                metadata.repository,
                "Issue Types",
                "Workflow",
                "Fields",
            ]:
                if expected_text not in settings_text:
                    raise AssertionError(
                        f'Step 4 failed: missing Settings text "{expected_text}". '
                        f"Observed Settings text: {settings_text}"
                    )

            for expected_item in (
                metadata.issue_types + metadata.statuses + metadata.fields
            ):
                if expected_item not in settings_text:
                    raise AssertionError(
                        f'Step 4 failed: expected metadata item "{expected_item}" was not rendered. '
                        f"Observed Settings text: {settings_text}"
                    )
    except (AssertionError, PlaywrightTimeoutError) as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        print(json.dumps(result, indent=2))
        raise
    else:
        result["status"] = "passed"
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
