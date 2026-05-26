from __future__ import annotations

from typing import Protocol


class TrackStateReleaseAssetReader(Protocol):
    def download_release_asset_bytes(self, asset_id: int) -> bytes: ...
