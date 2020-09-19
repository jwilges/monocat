import argparse
import logging
import os

from monocat.github import GitHubClient, ReleaseRequest

_logger = logging.getLogger(__name__)


class ReleaseError(RuntimeError):
    """A release error"""


class ReleaseManager:
    def __init__(self, owner: str, repository: str, interactive: bool):
        self.owner = owner
        self.repository = repository
        self.interactive = interactive
        self.client = GitHubClient(owner, repository)

    def list_releases(self):
        self.client.list_releases()

    def create_release(self):
        # TODO: JPW: Add `create_release` call.
        # self.client.create_release(ReleaseRequest())
        raise NotImplementedError('create_release is not currently supported')
