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

"""Test :mod:`simpl.rest`."""

import unittest

import bottle
import mock
import six

from simpl import rest


class TestBodyDecorator(unittest.TestCase):

    """Tests for :func:`simpl.rest.body`."""


    def test_decoration(self):
        """Test decorated function is called."""
        mock_handler = mock.Mock(return_value='X')
        decorated = rest.body()(mock_handler)
        self.assertTrue(callable(decorated))
        self.assertEqual(decorated(), 'X')
        mock_handler.assert_called_once()

    @mock.patch.object(rest.bottle, 'request')
    def test_schema(self, mock_request):
        """Test schema callable is called."""
        data = "100"
        mock_request.json = data
        mock_handler = mock.Mock()
        route = rest.body(schema=int)(mock_handler)
        route()
        mock_handler.assert_called_once_with(int(data))

    @mock.patch.object(rest.bottle, 'request')
    def test_schema_fail(self, mock_request):
        """Test schema is enforced."""
        mock_request.json = 'ALPHA'
        mock_handler = mock.Mock()
        route = rest.body(schema=int)(mock_handler)
        with self.assertRaises(bottle.HTTPError):
            route()

    @mock.patch.object(rest.bottle, 'request')
    def test_required(self, mock_request):
        """Test required is enforced."""
        mock_request.json = None
        mock_handler = mock.Mock()
        route = rest.body(required=True)(mock_handler)
        with self.assertRaises(bottle.HTTPError) as context:
            route()
        self.assertEqual(context.exception.body, 'Call body cannot be empty')

    @mock.patch.object(rest.bottle, 'request')
    def test_default(self, mock_request):
        """Test default is returned (and schema is applied to it)."""
        mock_request.json = None
        mock_handler = mock.Mock()
        route = rest.body(default='100', schema=int)(mock_handler)
        route()
        mock_handler.assert_called_once_with(100)


if __name__ == '__main__':
    unittest.main()
