from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class JD111IndexPageConfig:
    index_url: str
    expected_sections: tuple[str, ...]
    expected_feature_card_count: int
    expected_workflow_step_count: int


def load_jd_111_index_page_config() -> JD111IndexPageConfig:
    repository_root = Path(__file__).resolve().parents[3]
    default_index_url = (repository_root / "web" / "index.html").resolve().as_uri()
    return JD111IndexPageConfig(
        index_url=os.getenv("JD111_INDEX_URL", default_index_url),
        expected_sections=(
            "Browser Extensions",
            "Key Features",
            "AI Automation Workflow",
            "Tech Stack",
        ),
        expected_feature_card_count=4,
        expected_workflow_step_count=4,
    )
