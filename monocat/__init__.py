import argparse
import logging
import mimetypes
import os
from pathlib import Path
from typing import Optional, Sequence

from monocat.github import AssetRequest, AssetResponse, GitHubClient, ReleaseRequest, ReleaseResponse

_logger = logging.getLogger(__name__)


class ReleaseError(RuntimeError):
    """A release error"""


class ReleaseManager:
    def __init__(self, owner: str, repository: str, interactive: bool):
        self.owner = owner
        self.repository = repository
        self.interactive = interactive
        self.client = GitHubClient(owner, repository)

    def get_release(self, release_id: str) -> Optional[ReleaseResponse]:
        """Get a GitHub release by release identifier"""

        return self.client.get_release(release_id)

    def get_release_by_tag(self, tag: str) -> Optional[ReleaseResponse]:
        """Get a GitHub release by tag"""

        return self.client.get_release_by_tag(tag)

    def create_release(self, request: ReleaseRequest) -> ReleaseResponse:
        return self.client.create_release(request)

    def update_release(self, request: ReleaseRequest, release_id: int) -> ReleaseResponse:
        return self.client.update_release(request, release_id)

    def upload_assets(self, release: ReleaseResponse,
                      artifacts: Sequence[os.PathLike]) -> Sequence[AssetResponse]:
        response = []
        existing_asset_ids_by_name = {asset.name: asset.id for asset in release.assets}
        artifact_paths = [Path(artifact) for artifact in artifacts]
        for artifact_path in artifact_paths:
            asset = AssetRequest(name=artifact_path.name, label=artifact_path.name)
            with open(artifact_path, 'rb') as artifact_file:
                asset_id = existing_asset_ids_by_name.get(asset.name)
                # TODO: Add a force flag to automatically delete (and thus overwrite) existing assets.
                if not asset_id:
                    response.append(
                        self.client.upload_asset(
                            upload_url=release.upload_url, asset=asset, body=artifact_file.read()
                        )
                    )
        return response
