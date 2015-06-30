# Copyright (c) 2011-2015 Rackspace US, Inc.
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

"""Test :mod:`simpl.secrets`."""

import unittest

from simpl import secrets


class TestHideUrlPassword(unittest.TestCase):

    def test_http(self):
        hidden = secrets.hide_url_password('http://user:pass@localhost')
        self.assertEqual(hidden, 'http://user:*****@localhost')

    def test_mongo(self):
        hidden = secrets.hide_url_password('mongodb://user:pass@localhost/db')
        self.assertEqual(hidden, 'mongodb://user:*****@localhost/db')

    def test_git(self):
        hidden = secrets.hide_url_password('git+https://user:pass@github.com')
        self.assertEqual(hidden, 'git+https://user:*****@github.com')


if __name__ == '__main__':
    unittest.main()
