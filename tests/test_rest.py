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


class TestRangeResponse(unittest.TestCase):

    def tearDown(self):
        # reset the request object's headers and set the body to {}
        bottle.response.bind({})

    def test_negative_is_invalid(self):
        bottle.request.environ = {'QUERY_STRING': 'offset=-2'}
        kwargs = {}
        with self.assertRaises(ValueError):
            rest.validate_range_values(bottle.request, 'offset', kwargs)

    def test_non_numeric_is_invalid(self):
        bottle.request.environ = {'QUERY_STRING': 'limit=blah'}
        kwargs = {}
        with self.assertRaises(ValueError):
            rest.validate_range_values(bottle.request, 'limit', kwargs)

    def test_value_too_large(self):
        bottle.request.environ = {'QUERY_STRING': 'offset=20000000'}
        kwargs = {}
        with self.assertRaises(ValueError):
            rest.validate_range_values(bottle.request, 'offset', kwargs)

    def test_nothing_provided_is_valid_but_none(self):
        bottle.request.environ = {'QUERY_STRING': ''}
        kwargs = {}
        rest.validate_range_values(bottle.request, 'offset', kwargs)
        self.assertEqual(None, kwargs.get('offset'))
        self.assertEqual(200, bottle.response.status_code)

    def test_valid_number_passed_in_param(self):
        bottle.request.environ = {'QUERY_STRING': ''}
        kwargs = {'limit': '4236'}
        rest.validate_range_values(bottle.request, 'limit', kwargs)
        self.assertEqual(4236, kwargs['limit'])
        self.assertEqual(200, bottle.response.status_code)

    def test_valid_number_passed_in_request(self):
        bottle.request.environ = {'QUERY_STRING': 'offset=2'}
        kwargs = {}
        rest.validate_range_values(bottle.request, 'offset', kwargs)
        self.assertEqual(2, kwargs['offset'])
        self.assertEqual(200, bottle.response.status_code)

    def test_pagination_headers_no_ranges_no_results(self):
        rest.write_pagination_headers({'results': {}}, 0, None,
                                      bottle.response, '/widgets', 'widget')
        self.assertEqual(200, bottle.response.status_code)
        self.assertEqual(
            [
                ('Content-Range', 'widget 0-0/0'),
                ('Content-Type', 'text/html; charset=UTF-8')
            ],
            bottle.response.headerlist
        )

    def test_pagination_headers_unknown_count(self):
        rest.write_pagination_headers(
            {'results': {'1': {}}, 'collection-count': None},
            1, 1, bottle.response, '/widgets', 'widget')
        self.assertEqual(206, bottle.response.status_code)
        self.assertIn(
            ('Content-Range', 'widget 1-1/*'),
            bottle.response.headerlist
        )

    def test_pagination_headers_no_ranges_but_with_results(self):
        rest.write_pagination_headers(
            {
                'collection-count': 4,
                'results': {'1': {}, '2': {}, '3': {}, '4': {}}
            },
            0, None, bottle.response, '/fibbles', 'fibble'
        )
        self.assertEqual(200, bottle.response.status_code)
        self.assertEqual(
            [
                ('Content-Range', 'fibble 0-3/4'),
                ('Content-Type', 'text/html; charset=UTF-8')
            ],
            bottle.response.headerlist
        )

    def test_pagination_headers_with_ranges_and_within_results(self):
        rest.write_pagination_headers(
            {
                'collection-count': 4,
                'results': {'2': {}, '3': {}}
            },
            1, 2, bottle.response, '/widgets', 'widget'
        )
        self.assertEqual(206, bottle.response.status_code)
        six.assertCountEqual(self, [
            ('Link', '</widgets?limit=2>; rel="first"; '
                     'title="First page"'),
            ('Link', '</widgets?offset=2>; rel="last"; '
                     'title="Last page"'),
            ('Content-Range', 'widget 1-2/4'),
            ('Content-Type', 'text/html; charset=UTF-8')
        ], bottle.response.headerlist)

    def test_pagination_headers_with_all_links(self):
        rest.write_pagination_headers(
            {
                'collection-count': 8,
                'results': {'3': {}, '4': {}}
            },
            3, 2, bottle.response, '/widgets', 'widget'
        )
        self.assertEqual(206, bottle.response.status_code)
        six.assertCountEqual(self, [
            ('Link', '</widgets?limit=2>; rel="first"; '
                     'title="First page"'),
            ('Link', '</widgets?offset=6>; rel="last"; '
                     'title="Last page"'),
            ('Link', '</widgets?limit=2&offset=5>; rel="next"; '
                     'title="Next page"'),
            ('Link', '</widgets?limit=2&offset=1>; rel="previous"; '
                     'title="Previous page"'),
            ('Content-Range', 'widget 3-4/8'),
            ('Content-Type', 'text/html; charset=UTF-8')
        ], bottle.response.headerlist)

    def test_pagination_headers_last_page_overlap(self):
        rest.write_pagination_headers(
            {
                'collection-count': 4,
                'results': {'3': {}, '4': {}}
            },
            3, 3, bottle.response, '/widgets', 'widget'
        )
        self.assertEqual(206, bottle.response.status_code)
        self.assertIn(
            ('Link', '</widgets?offset=3>; rel="last"; title="Last page"'),
            bottle.response.headerlist)

    def test_pagination_no_count(self):
        rest.write_pagination_headers(
            {'data': ['A']},
            0, 1, bottle.response, '/fibbles', 'fibble'
        )
        self.assertEqual(206, bottle.response.status_code)
        self.assertIn(
            ('Content-Range', 'fibble 0-0/*'),
            bottle.response.headerlist
        )

    def test_paginated_decoration(self):
        """Test decorated function is called."""
        mock_handler = mock.Mock(return_value={})
        mock_handler.__name__ = "fxn"
        decorated = rest.paginated('widget')(mock_handler)
        self.assertTrue(callable(decorated))
        self.assertEqual(decorated(), {})
        mock_handler.assert_called_once()

    def test_paginated_validation(self):
        mock_handler = mock.Mock(return_value={})
        mock_handler.__name__ = "fxn"
        decorated = rest.paginated('widget')(mock_handler)
        self.assertIsNone(decorated(limit='invalid'))
        mock_handler.assert_not_called()

if __name__ == '__main__':
    unittest.main()
