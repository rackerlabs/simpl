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

"""Tests for log.py"""
from __future__ import print_function

import unittest

from simpl import log


class TestLogging(unittest.TestCase):

    """Tests for :mod:`log`."""

    def test_base(self):
        self.assertIsNotNone(log)


if __name__ == '__main__':
    unittest.main()
