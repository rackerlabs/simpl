# pylint: disable=C0103,C0111,R0903,R0904,W0212,W0232

# Copyright 2013-2015 Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for config.py"""
from __future__ import print_function

import os
import sys
import tempfile
import textwrap
import unittest

import mock

from simpl import config


class TestParsers(unittest.TestCase):
    def test_comma_separated_strings(self):
        expected = ['1', '2', '3']
        result = config.comma_separated_strings("1,2,3")
        self.assertItemsEqual(result, expected)

    def test_format_comma_separated_pairs(self):
        expected = dict(A='1', B='2', C='3')
        result = config.comma_separated_pairs("A=1,B=2,C=3")
        self.assertEqual(result, expected)


class TestConfig(unittest.TestCase):
    def test_instantiation(self):
        empty = config.Config(options=[])
        self.assertIsInstance(empty, config.Config)
        self.assertEqual(empty._values, {})

    def test_defaults(self):
        cfg = config.Config(options=[
            config.Option('--one', default=1),
            config.Option('--a', default='a'),
            config.Option('--none'),
        ])
        cfg.parse([])
        self.assertEquals(cfg.one, 1)
        self.assertEquals(cfg.a, 'a')
        self.assertIsNone(cfg.none)

    def test_items(self):
        cfg = config.Config(options=[
            config.Option('--one', default=1),
            config.Option('--none'),
        ])
        cfg.parse([])
        self.assertEquals(cfg.one, cfg['one'])
        self.assertEquals(cfg['one'], 1)
        self.assertIsNone(cfg['none'])

    @mock.patch.dict('os.environ', {'TEST_TWO': '2'})
    def test_required(self):
        self.assertEqual(os.environ['TEST_TWO'], '2')
        cfg = config.Config(options=[
            config.Option('--one', default=1, required=True),
            config.Option('--two', required=True, env='TEST_TWO'),
        ])
        cfg.parse([])
        self.assertEquals(cfg.one, 1)
        self.assertEquals(cfg.two, '2')

    def test_required_negative(self):
        cfg = config.Config(options=[
            config.Option('--required', required=True),
        ])
        with self.assertRaises(SystemExit):
            cfg.parse([])

    def test_argparser_groups(self):

        opts = [
            config.Option('--baz'),
            config.Option('--password', group='secret'),
            config.Option('--key', group='secret'),
            config.Option('--this', group='things'),
            config.Option('--that', group='things'),
            config.Option('--other', group='things'),
            config.Option('--who', group='group of its own'),
        ]
        myconf = config.Config(options=opts)
        parser = myconf.build_parser(opts)
        secret_group = None
        things_group = None
        own_group = None
        for grp in parser._action_groups:
            if grp.title == 'secret':
                secret_group = grp
            elif grp.title == 'things':
                things_group = grp
            elif grp.title == 'group of its own':
                own_group = grp
        self.assertTrue(secret_group)
        self.assertTrue(things_group)
        self.assertTrue(own_group)

        self.assertEqual(len(secret_group._group_actions), 2)
        option_strings = [i for k in secret_group._group_actions
                          for i in k.option_strings]
        self.assertIn('--password', option_strings)
        self.assertIn('--key', option_strings)
        self.assertEqual(len(things_group._group_actions), 3)
        option_strings = [i for k in things_group._group_actions
                          for i in k.option_strings]
        self.assertIn('--this', option_strings)
        self.assertIn('--that', option_strings)
        self.assertIn('--other', option_strings)
        self.assertEqual(len(own_group._group_actions), 1)
        option_strings = [i for k in own_group._group_actions
                          for i in k.option_strings]
        self.assertIn('--who', option_strings)

    def test_group_help_usage_output(self):

        opts = [
            config.Option('--baz'),
            config.Option('--password', group='secret'),
            config.Option('--key', group='secret', group_description='haha security'),
            config.Option('--this', group='things'),
            config.Option('--that', group='things', group_description='define me once'),
            config.Option('--other', group='things'),
            config.Option('--who', group='group of its own'),
        ]
        myconf = config.Config(options=opts)
        parser = myconf.build_parser(opts)
        helplines = [k.strip() for k in parser.format_help().splitlines()]
        self.assertIn('secret:', helplines)
        self.assertIn('haha security', helplines)
        self.assertIn('things:', helplines)
        self.assertIn('define me once', helplines)
        self.assertIn('group of its own:', helplines)

    @mock.patch.object(sys, 'stderr')
    def test_mutual_exclusion(self, mock_stderr):
        opts = [
            config.Option('--foo'),
            config.Option('--key', group='secret', mutually_exclusive=True),
            config.Option('--key-file', group='secret', dest='key',
                          mutually_exclusive=True, type=config.read_from),
            config.Option('--key-thing', group='secret'),
        ]

        # for read_from
        keystring = 'this-is-a-private-key'
        strfile = tempfile.NamedTemporaryFile()
        strfile.write('%s-written-to-file' % keystring)
        strfile.flush()

        myconf = config.Config(options=opts)
        argv = ['program', '--key-file', strfile.name,
                '--key', keystring]

        with self.assertRaises(SystemExit):
            try:
                myconf.parse(argv=argv)  # fails b/c mutual exclusion collision
            except SystemExit as err:
                errmsg = ('error: argument --key: '
                          'not allowed with argument --key-file')
                args, _ = mock_stderr.write.call_args
                self.assertIn(errmsg, args[0])
                raise

    @mock.patch.object(sys, 'stderr')
    def test_mutex_with_special_type(self, mock_stderr):
        opts = [
            config.Option('--foo'),
            config.Option('--key', group='secret', mutually_exclusive=True),
            config.Option('--key-file', group='secret', dest='key',
                          mutually_exclusive=True, type=config.read_from),
            config.Option('--key-thing', group='secret'),
            config.Option('--more', mutually_exclusive=True, dest='more',
                          action='store_true'),  # should be ok
            config.Option('--less', mutually_exclusive=True, dest='more',
                          action='store_false'),
        ]

        # for read_from
        keystring = 'this-is-a-private-key'
        strfile = tempfile.NamedTemporaryFile()
        strfile.write('%s-written-to-file' % keystring)
        strfile.flush()

        myconf = config.Config(options=opts)
        argv = ['program', '--key', keystring]
        myconf.parse(argv=argv)
        self.assertEqual(myconf.key, keystring)
        argv = ['program', '--key-file', strfile.name]
        myconf.parse(argv=argv)
        self.assertEqual(myconf.key, '%s-written-to-file' % keystring)

    def test_mutex_no_group_for_option_fail(self):
        opts = [
            config.Option('--ihavenogroup', mutually_exclusive=True,
                          action='store_true'),
        ]
        # mutual exclusion requires a group which is derived from
        # 'group' or 'dest'
        myconf = config.Config(options=opts)
        with self.assertRaises(config.NoGroupForOption):
            myconf.build_parser(opts)

    @mock.patch.object(sys, 'stderr')
    def test_mutually_exclusive_fails_lacking(self, mock_stderr):
        opts = [
            config.Option('--foo'),
            # if *any* arg in the same mutually_exclusive group says
            # required=True, then at least one value in that mutex group
            # will be required
            config.Option('--more', mutually_exclusive=True, dest='more',
                          action='store_true'),
            config.Option('--less', mutually_exclusive=True, dest='more',
                          action='store_false', required=True),
        ]
        myconf = config.Config(options=opts)
        argv = ['program', '--foo', 'myfoo']
        with self.assertRaises(SystemExit):
            try:
                myconf.parse(argv=argv)  # fails b/c mutual exclusion collision
            except SystemExit as err:
                errmsg = ('error: one of the '
                          'arguments --more --less is required')
                args, _ = mock_stderr.write.call_args
                self.assertIn(errmsg, args[0])
                raise

    @mock.patch.object(sys, 'stderr')
    def test_mutually_exclusive_fails_excess(self, mock_stderr):

        opts = [
            config.Option('--foo'),
            # if *any* arg in the same mutually_exclusive group says
            # required=True, then at least one value in that mutex group
            # will be required
            config.Option('--more', mutually_exclusive=True, dest='more',
                          action='store_true'),
            config.Option('--less', mutually_exclusive=True, dest='more',
                          action='store_false', required=True),
        ]
        myconf = config.Config(options=opts)
        argv = ['program', '--more', '--less']
        with self.assertRaises(SystemExit):
            try:
                myconf.parse(argv=argv)  # fails b/c mutual exclusion collision
            except SystemExit as err:
                errmsg = ('error: argument --less: '
                          'not allowed with argument --more')
                args, _ = mock_stderr.write.call_args
                self.assertIn(errmsg, args[0])
                raise

    def test_mutually_exclusive_dest(self):
        """Mutually exclusive group name derived from 'dest'."""
        opts = [
            # if *any* arg in the same mutually_exclusive group says
            # required=True, then at least one value in that mutex group
            # will be required
            config.Option('--more', mutually_exclusive=True, dest='more',
                          action='store_true'),
            config.Option('--less', mutually_exclusive=True, dest='more',
                          action='store_false'),
        ]
        myconf = config.Config(options=opts)
        argv = ['program']
        # testing that this raises no error
        myconf.parse(argv=argv)
        argv = ['program', '--more']
        myconf.parse(argv=argv)
        self.assertEqual(myconf.more, True)
        argv = ['program', '--less']
        myconf.parse(argv=argv)
        self.assertEqual(myconf.more, False)

    def test_default_metaconfig_options(self):

        myconf = config.Config()
        metaconf = myconf._get_metaconfig_class()
        self.assertEqual(metaconf, config.MetaConfig)
        self.assertEqual(len(metaconf.options), 1)
        self.assertEqual(metaconf.options[0].args, ('--ini',))

    def test_metaconfig_ini(self):

        metaconf = textwrap.dedent(
            """
            [default]
            ham = glam
            grand = slam

            [program]
            spam = rico
            grand = notpreferred
            """
        )
        opts = [
            config.Option('--ham', ini_section='default'),
            config.Option('--grand', ini_section='default'),
            config.Option('--spam'),
        ]
        strfile = tempfile.NamedTemporaryFile()
        strfile.write(metaconf)
        strfile.flush()
        argv = ['program', '--ini', strfile.name]
        myconf = config.Config(options=opts, argv=argv, prog='program')
        myconf.parse()
        self.assertEqual(myconf.grand, 'slam')
        self.assertEqual(myconf.ham, 'glam')
        self.assertEqual(myconf.spam, 'rico')

    def test_default_metaconfig_ini(self):
        """A default ini file is looked for by the metaconfig.

        Looks for '{cwd}/{prog}.ini' % (os.getcwd(), myconf.prog)
        """
        strfile = tempfile.NamedTemporaryFile(dir=os.getcwd(), suffix='.ini')
        prog = os.path.split(strfile.name)[-1].rsplit('.ini', 1)[0]
        metaconf = textwrap.dedent(
            """
            [%s]
            ham = glam
            grand = slam
            spam = rico
            """
        ) % prog
        opts = [
            config.Option('--ham'),
            config.Option('--grand'),
            config.Option('--spam'),
        ]
        strfile.write(metaconf)
        strfile.flush()
        argv = ['program', '--ini', strfile.name]
        myconf = config.Config(options=opts, argv=argv)
        myconf.prog = prog
        myconf.parse()
        self.assertEqual(myconf.grand, 'slam')
        self.assertEqual(myconf.ham, 'glam')
        self.assertEqual(myconf.spam, 'rico')


if __name__ == '__main__':
    unittest.main()
