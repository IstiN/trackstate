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
            test_directory="TS-540",
            ticket_key="TS-540",
            ticket_summary=(
                "Release-backed local-git attachment download succeeds through the "
                "GitHub Releases storage handler"
            ),
            test_file_path="testing/tests/TS-540/test_ts_540.py",
            run_command="python testing/tests/TS-540/test_ts_540.py",
            token_env_vars=("GH_TOKEN", "GITHUB_TOKEN"),
            provider_capability_product_gap=(
                "The local attachment-download path still fails through the "
                "provider-level GitHub Releases capability gate instead of "
                "delegating to the release storage handler."
            ),
            runtime_human_check=(
                "Verified the caller-visible JSON success response reported the "
                "release-backed local-git download, the observed authSource value, the "
                "manual.pdf attachment metadata, and the saved-file path."
            ),
            filesystem_human_check=(
                "Verified as a user that manual.pdf was actually written to the "
                "requested local path and that its bytes matched the GitHub Release "
                "asset exactly."
            ),
            expected_stdout_fragments=(
                '"authSource": "none"',
                f"/downloads/manual.pdf",
            ),
            required_data_keys_extra=("authSource",),
            required_data_values=(("authSource", "none"),),
        )
    )
    result, error = scenario.execute()
    print(json.dumps(result, indent=2, sort_keys=True))
    if error:
        raise SystemExit(error)


if __name__ == "__main__":
    main()
