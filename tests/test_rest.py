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
import webtest


class TestBodyDecorator(unittest.TestCase):

    """Tests for :func:`simpl.rest.body`."""

    def test_decoration(self):
        """Test decorated function is called."""
        mock_handler = mock.Mock(return_value='X')
        decorated = rest.body()(mock_handler)
        self.assertTrue(callable(decorated))
        self.assertEqual(decorated('arg', kwarg=2), 'X')
        mock_handler.assert_called_once_with(None, 'arg', kwarg=2)

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
        mock_handler.assert_called_once_with()

    def test_paginated_validation(self):
        mock_handler = mock.Mock(return_value={})
        mock_handler.__name__ = "fxn"
        decorated = rest.paginated('widget')(mock_handler)
        self.assertIsNone(decorated(limit='invalid'))
        mock_handler.assert_not_called()


class TestProcessParams(unittest.TestCase):

    """Tests for :func:`simpl.rest.process_prams`."""

    def test_filters(self):
        request = bottle.BaseRequest(environ={
            'QUERY_STRING': 'status=A&status=B,C&other=2'
        })
        expected = {'status': ['A', 'B', 'C'], 'other': '2'}
        results = rest.process_params(request,
                                      filter_fields=['status', 'other'])
        self.assertEqual(results, expected)

    def test_sort(self):
        request = bottle.BaseRequest(environ={
            'QUERY_STRING': 'sort=up&sort=-down'
        })
        expected = {'sort': ['up', '-down']}
        self.assertEqual(rest.process_params(request), expected)

    def test_standard(self):
        request = bottle.BaseRequest(environ={
            'QUERY_STRING': 'limit=100&offset=0&facets=status'
        })
        results = rest.process_params(request)
        self.assertEqual(results, {})

    def test_text(self):
        request = bottle.BaseRequest(environ={
            'QUERY_STRING': 'q=txt'
        })
        results = rest.process_params(request)
        self.assertEqual(results, {'q': ['txt']})

    def test_invalid(self):
        request = bottle.BaseRequest(environ={
            'QUERY_STRING': 'foo=bar'
        })
        with self.assertRaises(bottle.HTTPError):
            rest.process_params(request)

    def test_blank(self):
        request = bottle.BaseRequest(environ={
            'QUERY_STRING': ''
        })
        results = rest.process_params(request)
        self.assertEqual(results, {})

    def test_single(self):
        request = bottle.BaseRequest(environ={
            'QUERY_STRING': 'foo'
        })
        with self.assertRaises(bottle.HTTPError):
            rest.process_params(request)

    def test_strange(self):
        request = bottle.BaseRequest(environ={
            'QUERY_STRING': ',,\n??&&'
        })
        with self.assertRaises(bottle.HTTPError):
            rest.process_params(request)

    def test_dfaults(self):
        request = bottle.BaseRequest(environ={
            'QUERY_STRING': 'status=INACTIVE'
        })
        defaults = {'status': 'ACTIVE', 'size': 1}
        results = rest.process_params(request, filter_fields=defaults.keys(),
                                      defaults=defaults)
        self.assertEqual(results, {'status': 'INACTIVE', 'size': 1})


class TestAPIBasics(unittest.TestCase):

    """Test REST API routing and responses."""

    def setUp(self):
        """Init the tests by starting the bottle app and routes."""
        super(TestAPIBasics, self).setUp()
        app = bottle.Bottle()
        app.default_error_handler = rest.error_formatter
        self.app = webtest.TestApp(app)

        app.route('/', ['GET'], self.dummy_ok)
        app.route('/fail', ['GET'], self.dummy_fail)
        app.route('/bad', ['GET'], self.bad_code)
        app.route('/assert', ['GET'], self.dummy_assert)
        app.route('/unhandled', ['GET'], self.dummy_unhandled)

    @staticmethod
    def dummy_ok():
        """Dummy call for route testing."""
        return

    @staticmethod
    def dummy_fail():
        """Dummy call for route testing."""
        raise rest.HTTPError("Broken!", http_code=418, reason="Woops!")

    @staticmethod
    def bad_code():
        """Dummy call for route testing."""
        raise rest.HTTPError("wat?!", http_code=419, reason="Because")

    @staticmethod
    def dummy_assert():
        """Dummy call for route testing."""
        assert False, "Not what we expected"

    @staticmethod
    def dummy_unhandled():
        """Dummy call for route testing."""
        raise Exception("Possibly sensitive data")

    def test_default_404(self):
        res = self.app.get('/foo', expect_errors=True)
        self.assertEqual(res.status, '404 Not Found')
        self.assertEqual(res.content_type, 'application/json')
        expected = {
            'error': {
                'code': 404,
                'message': 'Not Found',
                'description': "Not found: '/foo'",
            }
        }
        self.assertEqual(res.json, expected)

    def test_default_405(self):
        res = self.app.post('/', expect_errors=True)
        self.assertEqual(res.status, '405 Method Not Allowed')
        self.assertEqual(res.content_type, 'application/json')
        expected = {
            'error': {
                'code': 405,
                'message': 'Method Not Allowed',
                'description': "Method not allowed.",
            }
        }
        self.assertEqual(res.json, expected)

    def test_raised_http_error(self):
        res = self.app.get('/fail', expect_errors=True)
        self.assertEqual(res.status, "418 I'm a teapot")
        self.assertEqual(res.content_type, 'application/json')
        expected = {
            'error': {
                'code': 418,
                'message': "I'm a teapot",
                'description': 'Broken!',
                'reason': "Woops!",
            }
        }
        self.assertEqual(res.json, expected)

    def test_bad_http_code(self):
        res = self.app.get('/bad', expect_errors=True)
        self.assertEqual(res.status, '419 Unknown')
        self.assertEqual(res.content_type, 'application/json')
        expected = {
            'error': {
                'code': 419,
                'message': "Unknown",
                'description': "wat?!",
                'reason': 'Because',
            }
        }
        self.assertEqual(res.json, expected)

    def test_asserts_become_500(self):
        res = self.app.get('/assert', expect_errors=True)
        self.assertEqual(res.status, '400 Bad Request')
        self.assertEqual(res.content_type, 'application/json')
        expected = {
            'error': {
                'code': 400,
                'message': 'Bad Request',
                'description': "Not what we expected",
            }
        }
        self.assertEqual(res.json, expected)

    def test_unhandled_500(self):
        res = self.app.get('/unhandled', expect_errors=True)
        self.assertEqual(res.status, '500 Internal Server Error')
        self.assertEqual(res.content_type, 'application/json')
        expected = {
            'error': {
                'code': 500,
                'message': 'Internal Server Error',
                'description': "Unexpected error",
            }
        }
        self.assertTrue(res.body.lower().find(b'internal') > 0)
        self.assertEqual(res.body.lower().find(b'sensitive'), -1)
        self.assertEqual(res.json, expected)

    def test_yaml(self):
        res = self.app.get('/foo',
                           headers={'Accept': 'application/x-yaml'},
                           expect_errors=True)
        self.assertEqual(res.content_type, 'application/x-yaml')
        expected = b"""\
error:
  code: 404
  description: 'Not found: ''/foo'''
  message: Not Found
"""
        self.assertEqual(res.body, expected)


if __name__ == '__main__':
    unittest.main()
