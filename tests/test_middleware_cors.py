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

"""Tests for CORS middleware."""

import wsgiref.util
import unittest

import mock
import six
from webtest.debugapp import debug_app

from simpl.middleware import cors


class TestCORSMiddleware(unittest.TestCase):

    def setUp(self):
        self.headers = []

    def start_response(self, status, headers, exc_info=None):
        """Emulate WSGI start_response."""
        self.headers += headers

    def test_default_bypass(self):
        """Default config ignores all calls."""
        middleware = cors.CORSMiddleware(debug_app)
        env = {'PATH_INFO': '/something/'}
        wsgiref.util.setup_testing_defaults(env)
        middleware(env.copy(), self.start_response)
        self.assertEqual(env['PATH_INFO'], '/something/')
        self.assertFalse(any(h[0] == 'Access-Control-Allow-Origin'
                             for h in self.headers))

    def test_netloc(self):
        """Netloc match adds headers."""
        middleware = cors.CORSMiddleware(debug_app,
                                         allowed_netlocs=["localhost"])
        env = {
            'REQUEST_METHOD': 'OPTIONS',
            'HTTP_ORIGIN': 'http://localhost',
        }
        wsgiref.util.setup_testing_defaults(env)
        middleware(env.copy(), self.start_response)
        six.assertCountEqual(self, self.headers, [
            ('Access-Control-Allow-Methods',
             ', '.join(cors.CORSMiddleware.default_methods)),
            ('Access-Control-Allow-Headers',
             ', '.join(cors.CORSMiddleware.default_headers)),
            ('Access-Control-Allow-Credentials', 'true'),
            ('Access-Control-Allow-Origin', 'http://localhost')])

    def test_netloc_mismatch(self):
        """Netloc match checks ports."""
        middleware = cors.CORSMiddleware(debug_app,
                                         allowed_netlocs=["localhost:9000"])
        env = {
            'REQUEST_METHOD': 'OPTIONS',
            'HTTP_ORIGIN': 'http://localhost:8080',
        }
        wsgiref.util.setup_testing_defaults(env)
        middleware(env.copy(), self.start_response)
        self.assertFalse(any(h[0] == 'Access-Control-Allow-Origin'
                             for h in self.headers))

    def test_hostname(self):
        """Hostname matches any port and adds headers."""
        middleware = cors.CORSMiddleware(debug_app,
                                         allowed_hostnames=["localhost"])
        env = {
            'REQUEST_METHOD': 'OPTIONS',
            'HTTP_ORIGIN': 'http://localhost:8080',
        }
        wsgiref.util.setup_testing_defaults(env)
        middleware(env.copy(), self.start_response)
        six.assertCountEqual(self, self.headers, [
            ('Access-Control-Allow-Methods',
             ', '.join(cors.CORSMiddleware.default_methods)),
            ('Access-Control-Allow-Headers',
             ', '.join(cors.CORSMiddleware.default_headers)),
            ('Access-Control-Allow-Credentials', 'true'),
            ('Access-Control-Allow-Origin', 'http://localhost:8080')])

    def test_regex(self):
        """Regex matches origin and adds headers."""
        middleware = cors.CORSMiddleware(debug_app, allowed_regexes=[".*"])
        env = {
            'REQUEST_METHOD': 'OPTIONS',
            'HTTP_ORIGIN': 'https://foo',
        }
        wsgiref.util.setup_testing_defaults(env)
        middleware(env.copy(), self.start_response)
        six.assertCountEqual(self, self.headers, [
            ('Access-Control-Allow-Methods',
             ', '.join(cors.CORSMiddleware.default_methods)),
            ('Access-Control-Allow-Headers',
             ', '.join(cors.CORSMiddleware.default_headers)),
            ('Access-Control-Allow-Credentials', 'true'),
            ('Access-Control-Allow-Origin', 'https://foo')])

    def test_conditional_import(self):
        """Fail to init if webob not installed."""
        with mock.patch('simpl.middleware.cors.webob', new=None):
            app = cors.CORSMiddleware(None)
            with self.assertRaises(RuntimeError):
                app({}, self.start_response)

if __name__ == '__main__':
    unittest.main()
