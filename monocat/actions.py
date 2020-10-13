import logging
from abc import ABC, abstractmethod
from typing import Sequence

from pydantic import BaseModel

from monocat import ReleaseManager
from monocat.github import AssetResponse, ReleaseRequest, ReleaseResponse


class CommandLineUpdateReleaseResponse(BaseModel):
    release: ReleaseResponse
    new_assets: Sequence[AssetResponse]


class Action(ABC):
    name: str
    description: str

    def __init__(self, release_manager: ReleaseManager):
        self._logger = logging.getLogger(
            '.'.join((self.__class__.__module__, self.__class__.__name__))
        )
        self.release_manager = release_manager

    @abstractmethod
    def __call__(self, argument_parser, arguments) -> bool:
        ...


class GetReleaseAction(Action):
    name: str = 'get-release'
    description: str = 'get an existing GitHub release identifier'

    def __call__(self, argument_parser, arguments) -> bool:
        if arguments.id:
            release = self.release_manager.get_release(arguments.id)
        else:
            release = self.release_manager.get_release_by_tag(arguments.tag)

        if release:
            if arguments.output_id:
                self._logger.info('%s', release.id)
            else:
                self._logger.info('%s', release.json(indent=2))

        return bool(release)


class UpdateReleaseAction(Action):
    name: str = 'update-release'
    description: str = 'update or create a GitHub release'

    def __call__(self, argument_parser, arguments) -> bool:
        if not arguments.id and not arguments.tag:
            argument_parser.error('at least one of the arguments --tag/-t --id/-i is required')

        existing_release = (
            self.release_manager.get_release(arguments.id)
            if arguments.id else self.release_manager.get_release_by_tag(arguments.tag)
        )
        existing_tag = existing_release.tag_name if existing_release else None
        request = ReleaseRequest(
            tag_name=arguments.tag if arguments.tag else existing_tag,
            name=arguments.name if arguments.name else arguments.tag,
            draft=arguments.draft,
            prerelease=arguments.prerelease
        )
        if arguments.commit:
            request.target_commitish = arguments.commit
        if arguments.body:
            request.body = arguments.body

        if existing_release:
            release = self.release_manager.update_release(request, existing_release.id)
        else:
            release = self.release_manager.create_release(request)

        if not release:
            return False

        assets = self.release_manager.upload_assets(release, arguments.artifacts)

        if arguments.output_id:
            self._logger.info('%s', release.id)
        else:
            self._logger.info(
                '%s',
                CommandLineUpdateReleaseResponse(release=release, new_assets=assets).json(indent=2)
            )

        all_uploads_successful = len(assets) == len(arguments.artifacts)
        if not all_uploads_successful:
            self._logger.warning(
                'One or more of the requested artifact(s) were not uploaded successfully; '
                'conflicting artifact(s) may already exist.'
            )

        return all_uploads_successful
