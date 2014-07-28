# pylint: disable=C0103,C0111,R0903,R0904,W0212,W0232

# Copyright (c) 2011-2013 Rackspace Hosting
# All Rights Reserved.
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Tests for common config."""
import os
import unittest

import mock

from waldo.contrib import config


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


if __name__ == '__main__':
    unittest.main()
