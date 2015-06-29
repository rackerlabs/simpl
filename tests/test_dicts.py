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

"""Tests for :mod:`dicts`"""

import copy
import re
import unittest

import mock
import six

from simpl.incubator import dicts


class TestSplitMergeDicts(unittest.TestCase):

    """Tests for split/merge dicts in :mod:`dicts`."""

    def test_split_dict_simple(self):
        fxn = dicts.split_dict
        self.assertEqual(fxn({}), ({}, None))
        combined = {
            'innocuous': 'Hello!',
            'password': 'secret',
        }
        innocuous = {'innocuous': 'Hello!'}
        secret = {'password': 'secret'}
        original = combined.copy()
        self.assertEqual(fxn(combined, filter_keys=[]), (combined, None))
        self.assertEqual(fxn(combined, ['password']), (innocuous, secret))
        self.assertDictEqual(combined, original)

    def test_split_dict_works_with_None_keys(self):
        filter_keys = [re.compile('quux')]
        data = {None: 'foobar'}
        expected = (data, None)
        self.assertEqual(expected,
                         dicts.split_dict(data, filter_keys))

    def test_extract_data_expression_as_filter(self):
        data = {
            "employee": {
                "name": "Bob",
                "title": "Mr.",
                "public_key": "rsa public key",
                "private_key": "a private key",
                "password": "password",
                "position": "left"
            },
            "server": {
                "access": {
                    "rootpassword": "password",
                    "server_privatekey": "private_key",
                    "server_public_key": "public_key"
                },
                "private_ip": "123.45.67.89",
                "public_ip": "127.0.0.1",
                "host_name": "server1"
            },
            "safe_val": "hithere",
            "secret_value": "Immasecret"
        }

        safe = {
            "employee": {
                "name": "Bob",
                "title": "Mr.",
                "public_key": "rsa public key",
                "position": "left"
            },
            "server": {
                "access": {
                    "server_public_key": "public_key"
                },
                "private_ip": "123.45.67.89",
                "public_ip": "127.0.0.1",
                "host_name": "server1"
            },
            "safe_val": "hithere",
        }

        secret = {
            "employee": {
                "private_key": "a private key",
                "password": "password",
            },
            "server": {
                "access": {
                    "rootpassword": "password",
                    "server_privatekey": "private_key",
                }
            },
            "secret_value": "Immasecret"
        }

        original_dict = copy.deepcopy(data)
        secret_keys = ["secret_value", re.compile("password"),
                       re.compile("priv(?:ate)?[-_ ]?key$")]
        body, hidden = dicts.split_dict(data, secret_keys)
        self.assertDictEqual(body, safe)
        self.assertDictEqual(secret, hidden)
        dicts.merge_dictionary(body, hidden)
        self.assertDictEqual(original_dict, body)

    def test_split_dict_complex(self):
        fxn = dicts.split_dict
        self.assertEqual(fxn({}), ({}, None))
        combined = {
            'innocuous': {
                'names': ['Tom', 'Richard', 'Harry']
            },
            'data': {
                'credentials': [{'password': 'secret', 'username': 'joe'}],
                'id': 1000,
                'list_with_only_cred_objects': [{'password': 'secret'}],
                'list_with_some_cred_objects': [
                    {
                        'password': 'secret',
                        'type': 'password',
                    },
                    'scalar',
                    {'name': 'joe'}
                ]
            }
        }
        innocuous = {
            'innocuous': {
                'names': ['Tom', 'Richard', 'Harry']
            },
            'data': {
                'id': 1000,
                'list_with_some_cred_objects': [
                    {
                        'type': 'password'
                    },
                    'scalar',
                    {'name': 'joe'}
                ]
            }
        }
        secret = {
            'data': {
                'credentials': [{'password': 'secret', 'username': 'joe'}],
                'list_with_only_cred_objects': [{'password': 'secret'}],
                'list_with_some_cred_objects': [
                    {
                        'password': 'secret'
                    },
                    None,
                    {}
                ]
            }
        }
        original = combined.copy()
        not_secret, is_secret = fxn(combined, [])
        self.assertDictEqual(not_secret, combined)
        self.assertIsNone(is_secret)

        not_secret, is_secret = fxn(combined, ['credentials', 'password'])
        self.assertDictEqual(not_secret, innocuous)
        self.assertDictEqual(is_secret, secret)
        self.assertDictEqual(combined, original)

        merged = dicts.merge_dictionary(innocuous, secret)
        self.assertDictEqual(original, merged)

    def test_extract_and_merge(self):
        fxn = dicts.split_dict
        data = {
            'empty_list': [],
            'empty_object': {},
            'null': None,
            'list_with_empty_stuff': [{}, None, []],
            'object_with_empty_stuff': {"o": {}, "n": None, 'l': []},
            "tree": {
                "array": [
                    {
                        "blank": {},
                        "scalar": 1
                    }
                ]
            }
        }
        result, _ = fxn(data, [])
        self.assertDictEqual(data, result)
        merge = dicts.merge_dictionary(data, data)
        self.assertDictEqual(data, merge)
        merge = dicts.merge_dictionary(data, {})
        self.assertDictEqual(data, merge)
        merge = dicts.merge_dictionary({}, data)
        self.assertDictEqual(data, merge)

    def test_merge_dictionary(self):
        dst = dict(
            a=1,  # not in source
            b=2,  # changed by source
            c=dict(  # deep merge check
                ca=31,
                cc=33,
                cd=dict(cca=1)
            ),
            d=4,
            f=6,
            g=7,
            i=[],  # add to empty list
            k=[3, 4],
            l=[[], [{'s': 1}]]
        )
        src = dict(
            b='u2',
            c=dict(
                cb='u32',
                cd=dict(
                    cda=dict(
                        cdaa='u3411',
                        cdab='u3412'
                    )
                )
            ),
            e='u5',
            h=dict(i='u4321'),
            i=[1],
            j=[1, 2],
            l=[None, [{'t': 8}]]
        )
        result = dicts.merge_dictionary(dst, src)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['a'], 1)
        self.assertEqual(result['d'], 4)
        self.assertEqual(result['f'], 6)
        self.assertEqual(result['b'], 'u2')
        self.assertEqual(result['e'], 'u5')
        self.assertIs(result['c'], dst['c'])
        self.assertIs(result['c']['cd'], dst['c']['cd'])
        self.assertEqual(result['c']['cd']['cda']['cdaa'], 'u3411')
        self.assertEqual(result['c']['cd']['cda']['cdab'], 'u3412')
        self.assertEqual(result['g'], 7)
        self.assertIs(src['h'], result['h'])
        self.assertEqual(result['i'], [1])
        self.assertEqual(result['j'], [1, 2])
        self.assertEqual(result['k'], [3, 4])
        self.assertEqual(result['l'], [[], [{'s': 1, 't': 8}]])

    def test_merge_lists(self):
        dst = [[], [2], [None, 4]]
        src = [[1], [], [3, None]]
        result = dicts.merge_lists(dst, src)
        self.assertIsInstance(result, list)
        self.assertEqual(result[0], [1])
        self.assertEqual(result[1], [2])
        self.assertEqual(result[2], [3, 4], "Found: %s" % result[2])

    def test_merge_dictionary_extend(self):
        dst = dict(
            a=[],
            b=[1],
            d=['a', 'b'],
            e=[1, 2, 3, 4]
        )
        src = dict(
            a=[1],  # append
            b=[1, 2],  # extend existing list
            c=[1],  # add new list
            d=[None, None, 'c'],
            e=[1, 2]
        )
        result = dicts.merge_dictionary(dst, src, extend_lists=True)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['a'], [1])
        self.assertEqual(result['b'], [1, 2])
        self.assertEqual(result['c'], [1])
        self.assertEqual(result['d'], ['a', 'b', None, None, 'c'])
        self.assertEqual(result['e'], [1, 2, 3, 4])


class TestDictPaths(unittest.TestCase):

    """Tests for :mod:`dicts` functions using paths as keys."""

    def test_write_path(self):
        cases = [
            {
                'name': 'scalar at root',
                'start': {},
                'path': 'root',
                'value': 'scalar',
                'expected': {'root': 'scalar'}
            }, {
                'name': 'int at root',
                'start': {},
                'path': 'root',
                'value': 10,
                'expected': {'root': 10}
            }, {
                'name': 'bool at root',
                'start': {},
                'path': 'root',
                'value': True,
                'expected': {'root': True}
            }, {
                'name': 'value at two piece path',
                'start': {},
                'path': 'root/subfolder',
                'value': True,
                'expected': {'root': {'subfolder': True}}
            }, {
                'name': 'value at multi piece path',
                'start': {},
                'path': 'one/two/three',
                'value': {},
                'expected': {'one': {'two': {'three': {}}}}
            }, {
                'name': 'add to existing',
                'start': {'root': {'exists': True}},
                'path': 'root/new',
                'value': False,
                'expected': {'root': {'exists': True, 'new': False}}
            }, {
                'name': 'overwrite existing',
                'start': {'root': {'exists': True}},
                'path': 'root/exists',
                'value': False,
                'expected': {'root': {'exists': False}}
            }
        ]
        for case in cases:
            result = case['start']
            dicts.write_path(result, case['path'], case['value'])
            self.assertEqual(result, case['expected'], msg=case['name'])

    def test_read_path(self):
        cases = [
            {
                'name': 'simple value',
                'start': {'root': 1},
                'path': 'root',
                'expected': 1
            }, {
                'name': 'simple path',
                'start': {'root': {'folder': 2}},
                'path': 'root/folder',
                'expected': 2
            }, {
                'name': 'blank path',
                'start': {'root': 1},
                'path': '',
                'expected': None
            }, {
                'name': '/ only',
                'start': {'root': 1},
                'path': '/',
                'expected': None
            }, {
                'name': 'extra /',
                'start': {'root': 1},
                'path': '/root/',
                'expected': 1
            }, {
                'name': 'nonexistent root',
                'start': {'root': 1},
                'path': 'not-there',
                'expected': None
            }, {
                'name': 'nonexistent path',
                'start': {'root': 1},
                'path': 'root/not/there',
                'expected': None
            }, {
                'name': 'empty source',
                'start': {},
                'path': 'root',
                'expected': None
            },
        ]
        for case in cases:
            result = dicts.read_path(case['start'], case['path'])
            self.assertEqual(result, case['expected'], msg=case['name'])

    def test_path_exists(self):
        cases = [
            {
                'name': 'simple value',
                'start': {'root': 1},
                'path': 'root',
                'expected': True
            }, {
                'name': 'simple path',
                'start': {'root': {'folder': 2}},
                'path': 'root/folder',
                'expected': True
            }, {
                'name': 'blank path',
                'start': {'root': 1},
                'path': '',
                'expected': False
            }, {
                'name': '/ only',
                'start': {'root': 1},
                'path': '/',
                'expected': True
            }, {
                'name': 'extra /',
                'start': {'root': 1},
                'path': '/root/',
                'expected': True
            }, {
                'name': 'nonexistent root',
                'start': {'root': 1},
                'path': 'not-there',
                'expected': False
            }, {
                'name': 'nonexistent path',
                'start': {'root': 1},
                'path': 'root/not-there',
                'expected': False
            }, {
                'name': 'empty source',
                'start': {},
                'path': 'root',
                'expected': False
            },
        ]
        for case in cases:
            result = dicts.path_exists(case['start'], case['path'])
            self.assertEqual(result, case['expected'], msg=case['name'])

if __name__ == '__main__':
    unittest.main()
