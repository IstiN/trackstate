from __future__ import annotations

from pathlib import Path

from testing.components.services.repository_release_tags_validator import (
    RepositoryReleaseTagsValidator,
)
from testing.core.config.repository_release_tags_config import (
    RepositoryReleaseTagsConfig,
)
from testing.core.interfaces.repository_release_tags_probe import (
    RepositoryReleaseTagsProbe,
)
from testing.frameworks.python.urllib_json_array_http_reader import (
    UrllibJsonArrayHttpReader,
)
from testing.frameworks.python.urllib_url_text_reader import UrllibUrlTextReader


def create_repository_release_tags_probe(
    repository_root: Path,
) -> RepositoryReleaseTagsProbe:
    config = RepositoryReleaseTagsConfig.from_file(
        repository_root / "testing/tests/TS-229/config.yaml"
    )
    return RepositoryReleaseTagsValidator(
        config,
        json_array_http_reader=UrllibJsonArrayHttpReader(),
        url_text_reader=UrllibUrlTextReader(),
    )
