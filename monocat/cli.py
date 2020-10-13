"""Command-line interface functionality for the Drover interface"""
import argparse
import logging
import sys
from typing import Optional

from monocat import ReleaseError, ReleaseManager
from monocat.__metadata__ import DESCRIPTION, VERSION
from monocat.actions import GetReleaseAction, UpdateReleaseAction

_logger = logging.getLogger(__name__)


class MaximumLogLevelLogFilter(logging.Filter):
    """A log filter to omit records greater or equal to a specified log level."""
    def __init__(self, maximum_level: int, name: str = ''):
        super().__init__(name=name)
        self.maximum_level = maximum_level

    def filter(self, record):
        return record.levelno < self.maximum_level


# yapf: disable
def _parse_update_release_arguments(root_subparsers):
    update_release_parser = root_subparsers.add_parser(UpdateReleaseAction.name, description=UpdateReleaseAction.description)

    update_release_parser.add_argument('--output-id', '-I', action='store_true', default=False,
                                       help='output only release identifier')

    update_release_parser.add_argument('--id', '-i', type=str,
                                       help='a GitHub release identifier')
    update_release_parser.add_argument('--tag', '-t', type=str,
                                       help='a git tag reference')

    update_release_parser.add_argument('--commit', '-c', type=str,
                                       help='a git commit object or an object that can be recursively dereferenced to a commit object')
    update_release_parser.add_argument('--name', '-n', type=str,
                                       help='the name of the release')
    update_release_parser.add_argument('--body', '-b', type=str,
                                       help='text describing the contents of the tag')
    update_release_parser.add_argument('--draft', '-d', action='store_true', default=False,
                                       help='create a draft (unpublished) release')
    update_release_parser.add_argument('--prerelease', '-p', action='store_true', default=False,
                                       help='identify the release as a prerelease')
    update_release_parser.add_argument('artifacts', type=str, nargs='*', metavar='artifact',
                                       help='a path name for a release artifact')


def _parse_get_release_arguments(root_subparsers):
    get_release_parser = root_subparsers.add_parser(GetReleaseAction.name, description=GetReleaseAction.description)

    get_release_parser.add_argument('--output-id', '-I', action='store_true', default=False,
                                       help='output only release identifier')

    group = get_release_parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--id', '-i', type=str,
                       help='a GitHub release identifier')
    group.add_argument('--tag', '-t', type=str,
                       help='a git tag reference')


def _parse_arguments():
    root_parser = argparse.ArgumentParser(description=DESCRIPTION)
    root_subparsers = root_parser.add_subparsers(dest='action', required=True)

    root_parser.add_argument('--version', '-V', action='version', version=f'%(prog)s {VERSION}')
    group = root_parser.add_mutually_exclusive_group()
    group.add_argument('--verbose', '-v', dest='verbosity', action='count', default=0,
                       help='increase output verbosity')
    group.add_argument('--quiet', '-q', dest='verbosity', action='store_const', const=None,
                       help='disable output')
    group = root_parser.add_mutually_exclusive_group()
    group.add_argument('--interactive', dest='interactive', action='store_true', default=sys.__stdin__.isatty(),
                       help='enable interactive output (i.e. for a PTY)')
    group.add_argument('--non-interactive', dest='interactive', action='store_false',
                       help='disable interactive output')

    root_parser.add_argument('--owner', '-o', action='store', type=str, required=True,
                             help='a GitHub repository owner')
    root_parser.add_argument('--repository', '-r', action='store', type=str, required=True,
                             help='a GitHub repository')

    _parse_update_release_arguments(root_subparsers)
    _parse_get_release_arguments(root_subparsers)

    return root_parser, root_parser.parse_args()


# yapf: enable
def _configure_logging(verbosity: Optional[int]):
    if verbosity is not None:
        console_level = max(1, logging.INFO - (10 * verbosity))
        console_formatter = logging.Formatter(fmt='%(message)s')
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.addFilter(MaximumLogLevelLogFilter(logging.WARNING))
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(console_level)
        error_formatter = logging.Formatter(fmt='%(levelname)s: %(message)s')
        error_handler = logging.StreamHandler(sys.stderr)
        error_handler.setFormatter(error_formatter)
        error_handler.setLevel(logging.WARNING)
        logging.basicConfig(handlers=(console_handler, error_handler), level=console_level)
        _logger.setLevel(console_level)
    else:
        logging.basicConfig(handlers=(logging.NullHandler(), ))


def main():
    """The main command-line entry point for the github-release-manager interface"""

    argument_parser, arguments = _parse_arguments()
    _configure_logging(arguments.verbosity)

    try:
        release_manager = ReleaseManager(
            arguments.owner, arguments.repository, interactive=arguments.interactive
        )
        actions = {
            action.name: action(release_manager)
            for action in (UpdateReleaseAction, GetReleaseAction)
        }
        response = actions[arguments.action](argument_parser, arguments)
        sys.exit(0 if response else 1)
    except ReleaseError as e:
        _logger.error('Release failed: %s', e)
        _logger.debug('', exc_info=e)
        sys.exit(1)
