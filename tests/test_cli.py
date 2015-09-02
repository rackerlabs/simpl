"""Functional tests for command line use."""

try:
    from StringIO import StringIO
except ImportError:
    # Python 3
    from io import StringIO

import subprocess
import sys
import unittest

import mock

from simpl import cli as simpl_cli
from simpl import server
from simpl.utils import cli as cli_utils


class TestSimplCLI(unittest.TestCase):

    def test_simpl_command_is_there(self):

        cmd = ['simpl', '--help']
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except (subprocess.CalledProcessError, OSError) as err:
            msg = 'Error while running `%s`' % subprocess.list2cmdline(cmd)
            self.fail(msg='%s --> %r' % (msg, err))

    def test_help_output(self):
        cmd = ['simpl', '--help']
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except (subprocess.CalledProcessError, OSError) as err:
            msg = 'Error while running `%s`' % subprocess.list2cmdline(cmd)
            self.fail(msg='%s --> %r' % (msg, err))
        self.assertIn('usage', str(output).lower())

    def test_simpl_global_parser(self):
        parser = simpl_cli.PARSER
        self.assertEqual(parser.prog, 'simpl')

    @mock.patch.object(server.bottle, 'run')
    def test_simpl_server(self, mock_bottle_run):
        simpl_cli.main(['server'])

    @mock.patch.object(server.bottle, 'run')
    def test_simpl_server_adapter_options(self, mock_bottle_run):
        simpl_cli.main(['server', '-o', 'great_option=real', 'verbose=1'])
        mock_bottle_run.assert_called_with(
            verbose='1', app=None, interval=1, quiet=False,
            server='xtornado', port=8080, host='127.0.0.1',
            debug=False, reloader=True, great_option='real')

    @mock.patch.object(server.bottle, 'run')
    def test_simpl_server_defaults(self, mock_bottle_run):
        simpl_cli.main(['server'])
        mock_bottle_run.assert_called_with(
            app=None, interval=1, quiet=False, server='xtornado', port=8080,
            host='127.0.0.1', debug=False, reloader=True)

    @mock.patch('sys.stderr', new_callable=StringIO)
    def test_simpl_server_fail(self, mock_stderr):
        with self.assertRaises(SystemExit):
            simpl_cli.main(['server', '--not-an-option'])
        mock_stderr.flush()
        mock_stderr.seek(0)
        self.assertIn('unrecognized arguments: --not-an-option',
                      mock_stderr.read())


class TestSimplCLIUtils(unittest.TestCase):

    @unittest.skipIf(sys.version_info >= (3, 0, 0),
                     "Skipping beyond python 3.")
    @mock.patch('sys.stderr', new_callable=StringIO)
    def test_helpfulparser(self, mock_stderr):
        parser = cli_utils.HelpfulParser()
        parser.add_subparsers()
        with self.assertRaises(SystemExit):
            parser.parse_args(args=[])
        mock_stderr.flush()
        mock_stderr.seek(0)
        output = mock_stderr.read()
        exp_regex = ('\nerror: too few arguments. Try getting '
                     'help with `.* --help`\n')
        self.assertRegexpMatches(output, exp_regex)

    def test_kwargs_succeed(self):

        expected = {
            'hello': 'world',
        }
        data = cli_utils.kwarg('hello=world')
        self.assertEqual(data, expected)

    def test_kwargs_fail(self):

        strings = [
            # cannot start with a delimiter
            '=world'
            # cannot end with the delimiter
            'more=',
            # must have at least one pair
            'true',
        ]
        for string in strings:
            with self.assertRaises(ValueError):
                data = cli_utils.kwarg(string)


if __name__ == '__main__':
    unittest.main()
