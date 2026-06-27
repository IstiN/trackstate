#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.core.config.setup_repo_smoke_config import load_setup_repo_smoke_config
from testing.frameworks.python.setup_repo_smoke_framework import SetupRepoSmokeFramework

OUTPUTS_DIR = REPO_ROOT / "outputs"
RESULT_PATH = OUTPUTS_DIR / "setup_repo_smoke_result.json"


def main() -> int:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_setup_repo_smoke_config()
    framework = SetupRepoSmokeFramework(config)

    result = framework.run()

    payload = result.to_dict()
    RESULT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    print(json.dumps(payload, indent=2, sort_keys=True))

    if result.errors:
        print("\nFAILURES:", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if result.pages_health and not result.pages_health.healthy:
        print("\nPages health check failed.", file=sys.stderr)
        return 1

    if result.pages_interactive and not result.pages_interactive.within_budget:
        print("\nPages interactive budget exceeded.", file=sys.stderr)
        return 1

    if result.cli_smoke and not result.cli_smoke.all_succeeded:
        print("\nCLI smoke path failed.", file=sys.stderr)
        return 1

    if result.cli_benchmark and not result.cli_benchmark.passed:
        print("\nCLI benchmark failed.", file=sys.stderr)
        return 1

    print("\nAll setup-repo smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
