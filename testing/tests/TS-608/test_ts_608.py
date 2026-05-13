from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE_TEST_PATH = REPO_ROOT / "testing/tests/TS-484/test_ts_484.py"


def _load_base_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ts484_hosted_release_replacement", BASE_TEST_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load base hosted replacement test: {BASE_TEST_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE_MODULE = _load_base_module()
BASE_MODULE.TICKET_KEY = "TS-608"
BASE_MODULE.ISSUE_SUMMARY = "TS-608 byte-level hosted GitHub Release replacement fixture"


def main() -> None:
    BASE_MODULE.main()


if __name__ == "__main__":
    main()
