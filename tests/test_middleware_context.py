# pylint: disable=C0103,R0904,R0903

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

"""Tests for Context middleware."""

import unittest

import mock
from webtest.debugapp import debug_app

from simpl.middleware import context
from simpl import threadlocal


class TestContextMiddleware(unittest.TestCase):

    def setUp(self):
        super(TestContextMiddleware, self).setUp()
        self.filter = context.ContextMiddleware(debug_app)
        self.headers = []
        # Disable clearing the context
        self.patcher = mock.patch.object(threadlocal.ThreadLocalDict, 'clear')
        self.mock = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        threadlocal.default().clear()
        super(TestContextMiddleware, self).tearDown()

    def start_response(self, status, headers, exc_info=None):
        """Emulate WSGI start_response."""
        self.headers += headers

    def test_url_override(self):
        env = {'REQUEST_METHOD': 'GET',
               'PATH_INFO': '/'}
        self.filter.override_url = "http://OVERRIDDEN"
        self.filter(env, self.start_response)
        self.assertEqual('http://OVERRIDDEN', env['context']['base_url'])

    def test_no_url_scheme(self):
        with self.assertRaises(KeyError):
            self.filter({}, self.start_response)

    def test_http_host(self):
        env = {'REQUEST_METHOD': 'GET',
               'PATH_INFO': '/',
               'wsgi.url_scheme': 'http',
               'HTTP_HOST': 'MOCK'}
        self.filter(env, self.start_response)
        self.assertEqual('http://MOCK', env['context']['base_url'])

    def test_server_name(self):
        env = {'REQUEST_METHOD': 'GET',
               'PATH_INFO': '/',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'MOCK',
               'SERVER_PORT': '80'}
        self.filter(env, self.start_response)
        self.assertEqual('http://MOCK', env['context']['base_url'])

    def test_https_weird_port(self):
        env = {'REQUEST_METHOD': 'GET',
               'PATH_INFO': '/',
               'wsgi.url_scheme': 'https',
               'SERVER_NAME': 'MOCK',
               'SERVER_PORT': '444'}
        self.filter(env, self.start_response)
        self.assertEqual('https://MOCK:444', env['context']['base_url'])

    def test_http_weird_port(self):
        env = {'REQUEST_METHOD': 'GET',
               'PATH_INFO': '/',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'MOCK',
               'SERVER_PORT': '81'}
        self.filter(env, self.start_response)
        self.assertEqual('http://MOCK:81', env['context']['base_url'])

    @mock.patch.object(context.uuid, 'uuid4')
    def test_transaction_id(self, mock_uuid):
        mock_uuid.return_value = mock.Mock(hex="12345abc")
        env = {'REQUEST_METHOD': 'GET',
               'PATH_INFO': '/',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'MOCK',
               'SERVER_PORT': '80'}
        self.filter(env, self.start_response)
        self.assertIn(('X-Transaction-Id', '12345abc'), self.headers)
        self.assertIn('transaction_id', env['context'])
        self.assertEqual('12345abc', env['context']['transaction_id'])


class TestContextCleanup(unittest.TestCase):

    """Verify that context data is cleared after a request."""

    def setUp(self):
        self.filter = context.ContextMiddleware(debug_app)
        self.headers = []

    def start_response(self, status, headers, exc_info=None):
        """Emulate WSGI start_response."""
        self.headers += headers

    def test_request(self):
        env = {'REQUEST_METHOD': 'GET',
               'PATH_INFO': '/'}
        self.filter(env, self.start_response)
        self.assertEqual(threadlocal.default(), {})

if __name__ == '__main__':
    unittest.main()
