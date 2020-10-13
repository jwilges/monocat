import logging
import sys

from contextlib import ExitStack
from unittest import TestCase
from unittest.mock import DEFAULT as DEFAULT_MOCK
from unittest.mock import MagicMock, patch

from monocat import cli


class TestConfigureLogging(TestCase):
    # TODO: Reduce `_configure_logging` test complexity by decoupling parsed verbosity <-> log level mapping (among other things).

    def test_verbosity_none_configures_null_handler(self):
        expected_verbosity_argument = None
        mock_arguments = MagicMock()
        mock_arguments.verbosity = expected_verbosity_argument
        with ExitStack() as _scope:
            mock_logging = _scope.enter_context(
                patch.multiple('logging', basicConfig=DEFAULT_MOCK, getLogger=DEFAULT_MOCK))
            cli._configure_logging(expected_verbosity_argument)

            mock_logging['basicConfig'].assert_called_once()
            mock_basic_config_kwargs = mock_logging['basicConfig'].mock_calls[0].kwargs
            assert isinstance(mock_basic_config_kwargs['handlers'][0], logging.NullHandler)

    def test_verbosity_nonzero_configures_logging(self):
        # Expectation:
        #   verbosity argument = 1 (i.e. `-v`) should yield a console log level of: INFO (20) - (10 * 1) = 10
        expected_verbosity_argument = 1
        expected_verbosity = 10
        mock_arguments = MagicMock()
        mock_arguments.verbosity = expected_verbosity_argument
        with ExitStack() as _scope:
            mock_logging = _scope.enter_context(
                patch.multiple('logging', basicConfig=DEFAULT_MOCK, getLogger=DEFAULT_MOCK))
            cli._configure_logging(expected_verbosity_argument)

            mock_logging['basicConfig'].assert_called_once()
            mock_basic_config_kwargs = mock_logging['basicConfig'].mock_calls[0].kwargs

            assert mock_basic_config_kwargs['level'] == expected_verbosity

            stdout_handlers = (
                handler for handler in mock_basic_config_kwargs['handlers']
                if isinstance(handler, logging.StreamHandler) and handler.stream.name == sys.stdout.name
            )
            assert stdout_handlers
            assert all(handler.level == expected_verbosity for handler in stdout_handlers)

            stderr_handlers = (
                handler for handler in mock_basic_config_kwargs['handlers']
                if isinstance(handler, logging.StreamHandler) and handler.stream.name == sys.stderr.name
            )
            assert stderr_handlers
            assert all(handler.level == logging.WARNING for handler in stderr_handlers)


class TestMain(TestCase):
    # TODO: `main` test complexity by decoupling `Action`-related mappings.

    def test_log_configuration(self):
        expected_verbosity = 1
        mock_parse_arguments = MagicMock(
            return_value=(
                MagicMock(),
                MagicMock(verbosity=expected_verbosity, action='get-release')
            ))
        mock_configure_logging = MagicMock()
        with ExitStack() as _scope:
            _scope.enter_context(
                patch.object(cli.sys, 'exit'))
            _scope.enter_context(
                patch.object(cli, '_parse_arguments', mock_parse_arguments))
            _scope.enter_context(
                patch.object(cli, '_configure_logging', mock_configure_logging))
            _scope.enter_context(
                patch.object(cli, 'ReleaseManager'))
            _scope.enter_context(
                patch.object(cli.GetReleaseAction, '__call__')
            )
            cli.main()

            mock_parse_arguments.assert_called()
            mock_configure_logging.assert_called_with(expected_verbosity)
