# pylint: disable=R0904,W0212

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
import unittest

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


if __name__ == '__main__':
    unittest.main()
