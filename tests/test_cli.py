from contextlib import ExitStack
from unittest.mock import MagicMock, patch
from unittest.mock import DEFAULT as DEFAULT_MOCK
from unittest import TestCase

from monocat import cli

class TestMain(TestCase):
    def test_verbosity_none_skips_log_configuration(self):
        mock_arguments = MagicMock()
        mock_arguments.verbosity = None
        with ExitStack() as _scope:
            mock_logging = _scope.enter_context(
                patch.multiple('logging', basicConfig=DEFAULT_MOCK, getLogger=DEFAULT_MOCK))
            _scope.enter_context(
                patch.object(cli, '_parse_arguments', return_value=mock_arguments))
            _scope.enter_context(
                patch.object(cli, 'ReleaseManager'))
            cli.main()

            mock_logging['basicConfig'].assert_not_called()
            mock_logging['getLogger'].assert_not_called()

    def test_verbosity_nonzero_skips_log_configuration(self):
        mock_arguments = MagicMock()
        mock_arguments.verbosity = 1
        with ExitStack() as _scope:
            mock_logging = _scope.enter_context(
                patch.multiple('logging', basicConfig=DEFAULT_MOCK, getLogger=DEFAULT_MOCK))
            _scope.enter_context(
                patch.object(cli, '_parse_arguments', return_value=mock_arguments))
            _scope.enter_context(
                patch.object(cli, 'ReleaseManager'))
            cli.main()

            mock_logging['basicConfig'].assert_called()
            mock_logging['getLogger'].assert_called()
