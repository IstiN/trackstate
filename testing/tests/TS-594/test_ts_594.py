from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.tests.support.trackstate_cli_release_download_success_scenario import (  # noqa: E402
    TrackStateCliReleaseDownloadSuccessScenario,
    TrackStateCliReleaseDownloadSuccessScenarioOptions,
)


def main() -> None:
    scenario = TrackStateCliReleaseDownloadSuccessScenario(
        options=TrackStateCliReleaseDownloadSuccessScenarioOptions(
            repository_root=REPO_ROOT,
            test_directory="TS-594",
            ticket_key="TS-594",
            ticket_summary=(
                "Local release-backed download succeeds with valid authentication and remotes"
            ),
            test_file_path="testing/tests/TS-594/test_ts_594.py",
            run_command="python testing/tests/TS-594/test_ts_594.py",
            token_env_vars=("TRACKSTATE_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"),
            provider_capability_product_gap=(
                "The local release-backed download still fails through the provider "
                "capability gate instead of allowing a valid authenticated request "
                "to reach the GitHub Releases download path."
            ),
            runtime_human_check=(
                "Verified the caller-visible JSON success response showed `ok: true`, "
                "the `local-git` provider, the local target path, and the "
                "`manual.pdf` attachment metadata in the right success state."
            ),
            filesystem_human_check=(
                "Verified as a user that `manual.pdf` was actually written to the "
                "requested local path and opening it showed the expected attachment "
                "text seeded into the live release asset."
            ),
            expected_stdout_fragments=(
                '"ok": true',
                '"type": "local"',
            ),
            expected_file_text_fragment=(
                "TS-594 successful release-backed local download fixture."
            ),
        )
    )
    result, error = scenario.execute()
    print(json.dumps(result, indent=2, sort_keys=True))
    if error:
        raise SystemExit(error)


if __name__ == "__main__":
    main()
