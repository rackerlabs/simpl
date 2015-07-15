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

"""Tests for :mod:`simpl.incubator.rest`."""

import unittest

import bottle
from simpl.incubator import rest
import voluptuous as volup
import webtest


class TestSchemaDecorator(unittest.TestCase):

    def setUp(self):
        self.root_app = bottle.Bottle()
        self.app = webtest.TestApp(self.root_app)

        def callback(body=None, query=None):
            return dict(body=body, query=query)
        self.callback = callback

    def test_no_schema(self):
        # Use the decorator without the @ syntax:
        self.callback = rest.schema()(self.callback)

        self.root_app.route('/foo', callback=self.callback)
        result = self.app.get('/foo')
        self.assertEqual(dict(body=None, query=None), result.json)

    def test_no_schema_with_body(self):
        self.callback = rest.schema()(self.callback)

        self.root_app.route('/foo', method='POST', callback=self.callback)
        result = self.app.post_json('/foo', params={'a': 1})
        self.assertEqual(dict(body={'a': 1}, query=None), result.json)

    def test_body_schema_no_body(self):
        body_schema = volup.Schema({
            'a': int,
            'b': [str],
        })
        self.callback = rest.schema(body_schema=body_schema)(self.callback)

        self.root_app.route('/foo', method='POST', callback=self.callback)
        # Empty request body
        result = self.app.post_json('/foo', expect_errors=True)

        self.assertEqual(400, result.status_int)

    def test_body_schema_with_body(self):
        body_schema = volup.Schema({
            'a': volup.Coerce(int),
            'b': [volup.Coerce(str)],
        })
        self.callback = rest.schema(body_schema=body_schema)(self.callback)

        self.root_app.route('/foo', method='POST', callback=self.callback)
        result = self.app.post_json('/foo', dict(a='1', b=['foo', 'bar']),
                                    expect_errors=True)

        self.assertEqual(
            # Note that `a` in the body is converted to an int.
            dict(body=dict(a=1, b=['foo', 'bar']), query=None),
            result.json
        )

    def test_no_schema_with_query(self):
        self.callback = rest.schema()(self.callback)

        self.root_app.route('/foo', callback=self.callback)
        result = self.app.get('/foo?a=1&b=2&a=foo')

        self.assertEqual(
            dict(body=None, query=dict(b=['2'], a=['1', 'foo'])),
            result.json
        )

    def test_no_schema_with_body_and_query(self):
        self.callback = rest.schema()(self.callback)

        self.root_app.route('/foo', method='POST', callback=self.callback)
        result = self.app.post_json(
            '/foo?a=1&b=2&a=foo',
            dict(d='3', e=['4', 'bar'])
        )
        self.assertEqual(
            {'body': {'d': '3', 'e': ['4', 'bar']},
             'query': {'a': ['1', 'foo'], 'b': ['2']}},
            result.json
        )

    def test_body_required_body_empty(self):
        self.callback = rest.schema(body_required=True)(self.callback)

        self.root_app.route('/foo', method='POST', callback=self.callback)
        result = self.app.post_json('/foo', expect_errors=True)

        self.assertEqual(400, result.status_int)

    def test_query_schema(self):
        self.callback = rest.schema(query_schema=volup.Schema({
            'a': rest.coerce_one(str),
            'b': rest.coerce_many(int),
        }))(self.callback)

        self.root_app.route('/foo', callback=self.callback)
        result = self.app.get('/foo?a=foo&b=1&b=2&b=3')

        self.assertEqual(
            dict(body=None, query=dict(a='foo', b=[1, 2, 3])),
            result.json
        )

    def test_query_schema_fail(self):
        self.callback = rest.schema(query_schema=volup.Schema({
            'a': rest.coerce_one(str),
            'b': rest.coerce_many(int),
        }))(self.callback)

        self.root_app.route('/foo', callback=self.callback)
        # There are two values for `a`. We only expect one.
        result = self.app.get('/foo?a=foo&b=bar&b=2&b=3', expect_errors=True)

        self.assertEqual(400, result.status_int)


class TestMultiValidationError(unittest.TestCase):

    """Tests for :class:`chessboard.parser.MultiValidationError`.

    Mostly, we need to tests the formatting of error messages.
    """

    def test_error_formatting(self):
        """Test the formatting of error paths."""
        schema = volup.Schema({
            volup.Required('foo'): volup.Schema({
                volup.Required('id'): str,
                volup.Required('name'): str,
                volup.Optional('description'): str,
            }),
        })

        input_data = {
            'foo': {
                'id': 124,
                'name': 'test',
            },
            'extra': 0,
        }
        with self.assertRaises(volup.MultipleInvalid) as mi:
            schema(input_data)

        mve = rest.MultiValidationError(mi.exception.errors)
        expected_str = """\
['extra']: extra keys not allowed
['foo']['id']: expected str"""

        expected_repr = """\
MultiValidationError(
\t['extra']: extra keys not allowed
\t['foo']['id']: expected str
)"""

        expected_message = (
            "['extra']: extra keys not allowed\n"
            "['foo']['id']: expected str"
        )

        self.assertEqual(expected_str, str(mve))
        self.assertEqual(expected_repr, repr(mve))
        self.assertEqual(expected_message, mve.message)


