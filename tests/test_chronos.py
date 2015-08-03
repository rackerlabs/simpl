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

"""Tests for :mod:`chronos`."""

import datetime
import time
import unittest

import mock

from simpl import chronos


class TestChronos(unittest.TestCase):

    def test_get_time_string(self):
        some_time = time.gmtime(0)
        with mock.patch.object(chronos.time, 'gmtime') as mock_gmt:
            mock_gmt.return_value = some_time
            result = chronos.get_time_string()
            self.assertEqual(result, "1970-01-01T00:00:00Z")

    def test_get_time_string_with_time(self):
        result = chronos.get_time_string(time_gmt=time.gmtime(0))
        self.assertEqual(result, "1970-01-01T00:00:00Z")

    def test_get_time_string_with_datetime(self):
        result = chronos.get_time_string(
            time_gmt=datetime.datetime(2015, 8, 3, 10, 53, 42))
        self.assertEqual(result, "2015-08-03T10:53:42Z")

    def test_get_time_string_with_invalid(self):
        with self.assertRaises(TypeError):
            chronos.get_time_string(self)

    def test_parse_time_string(self):
        result = chronos.parse_time_string("2015-10-11T22:33:44Z")
        self.assertEqual(result, datetime.datetime(2015, 10, 11, 22, 33, 44))


if __name__ == '__main__':
    unittest.main()
