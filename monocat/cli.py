"""Command-line interface functionality for the Drover interface"""
import argparse
import logging
import sys

from monocat import ReleaseManager, ReleaseError
from monocat.__metadata__ import __version__

_logger = logging.getLogger(__name__)


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.partition('\n')[0])
    parser.add_argument('--version', '-V', action='version', version=f'%(prog)s {__version__}')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--verbose', '-v', dest='verbosity', action='count', default=0,
                       help='increase output verbosity')
    group.add_argument('--quiet', dest='verbosity', action='store_const', const=None,
                       help='disable output')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--interactive', dest='interactive', action='store_true', default=sys.__stdin__.isatty(),
                       help='enable interactive output (i.e. for a PTY)')
    group.add_argument('--non-interactive', dest='interactive', action='store_false',
                       help='disable interactive output')

    parser.add_argument('--owner', '-o', action='store', type=str, required=True)
    parser.add_argument('--repository', '-r', action='store', type=str, required=True)

    return parser.parse_args()


def main():
    """The main command-line entry point for the github-release-manager interface"""
    arguments = _parse_arguments()

    if arguments.verbosity is not None:
        logging.basicConfig(format='%(message)s', stream=sys.stdout)
        logging_level = max(1, logging.INFO - (10 * arguments.verbosity))
        logging.getLogger(__name__.split('.')[0]).setLevel(logging_level)

    try:
        release_manager = ReleaseManager(arguments.owner, arguments.repository, interactive=arguments.interactive)
        release_manager.create_release()
    except ReleaseError as e:
        _logger.error('Release failed: %s', e)
        _logger.debug('', exc_info=e)
        sys.exit(1)
