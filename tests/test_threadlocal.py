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
#

"""Tests for threadlocal dict module."""

import random
import string
import threading
import unittest

from six.moves import queue
from six.moves import xrange

from simpl import threadlocal


class TestThreadLocal(unittest.TestCase):

    def setUp(self):
        # clear the threadlocal dict
        threadlocal.default().clear()

    def get_some_text(self, length=16):
        return ''.join(
            [random.choice(string.ascii_letters) for _ in xrange(length)])

    def test_default(self):
        self.assertIs(threadlocal.default(), threadlocal.CONTEXT)

    def test_threadlocal_dict_repr(self):
        tld = threadlocal.default()
        tld['good'] = 'glob'
        repr_str = repr(tld)
        expected = "<ThreadLocalDict {'good': 'glob'}>"
        self.assertEqual(repr_str, expected)

    def test_correct_threadlocal_dicts(self):
        key = 'value'
        num_threads = 5

        def get_tld(container):
            current = threadlocal.default()
            current[key] = self.get_some_text()
            container.put(current._get_local_dict())

        local_dicts = queue.Queue()
        threads = []
        for _ in xrange(num_threads):
            t = threading.Thread(target=get_tld, args=(local_dicts,))
            t.start()
            threads.append(t)
        # and one to grow on
        threadlocal.default()[key] = self.get_some_text()
        local_dicts.put(threadlocal.default()._get_local_dict())

        for thread in threads:
            thread.join()

        values = set()
        while not local_dicts.empty():
            tld = local_dicts.get(block=False)
            values.add(tld[key])

        # assert 6 dicts were created with 6 different values
        self.assertEqual(len(values), num_threads+1)

    def test_non_default_namespace(self):
        tld = threadlocal.default()
        another = threadlocal.ThreadLocalDict('custom_namespace')
        self.assertIsNot(tld._get_local_dict(), another._get_local_dict())

    def test_default_namespace(self):
        tld = threadlocal.default()
        another = threadlocal.ThreadLocalDict(threadlocal.DEFAULT_NAMESPACE)
        self.assertIs(tld._get_local_dict(), another._get_local_dict())

    def test_equality_same_namespace(self):
        namespace = self.get_some_text()
        instance_one = threadlocal.ThreadLocalDict(namespace)
        instance_two = threadlocal.ThreadLocalDict(namespace)
        self.assertEqual(instance_one, instance_two)

    def test_equality_different_namespace(self):
        key, value = 'key', 'value'
        instance_one = threadlocal.ThreadLocalDict('foo')
        instance_one[key] = value
        instance_two = threadlocal.ThreadLocalDict('bar')
        instance_two[key] = value
        self.assertEqual(instance_one, instance_two)

    def test_not_same(self):
        namespace = self.get_some_text()
        instance_one = threadlocal.ThreadLocalDict(namespace)
        instance_two = threadlocal.ThreadLocalDict(namespace)
        self.assertIsNot(instance_one, instance_two)

if __name__ == '__main__':
    unittest.main()
