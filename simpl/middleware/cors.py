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

"""CORS WSGI Middleware.

Example:

    # Disable all CORS checks:
    import bottle
    from simpl.middleware import cors

    app = bottle.default_app()
    chain = cors.CORSMiddleware(app, allowed_regexes=['.*'])
    bottle.run(app=chain)
"""

import logging
import re

from six.moves.urllib import parse
try:
    import webob
except ImportError:
    webob = None

LOG = logging.getLogger(__name__)


class CORSMiddleware(object):  # pylint: disable=R0903

    """Responds to CORS requests."""

    default_methods = ('GET', 'OPTIONS', 'POST', 'PUT', 'HEAD', 'DELETE')
    default_headers = (
        'Accept',
        'Connection',
        'Content-Length',
        'Content-Type',
        'Accept-Language',
        'Accept-Encoding',
        'User-Agent',
        'X-CSRF-Token',
        'X-Requested-With',
    )

    def __init__(self, app,
                 allowed_netlocs=None,
                 allowed_hostnames=None,
                 allowed_headers=default_headers,
                 allowed_methods=default_methods,
                 allowed_regexes=None):
        """Determine what requests to allow.

        :keyword allowed_netlocs: includes port (ex localhost:8080)
        :keyword allowed_hostnames: names, FQDNs or IP addresses
        :keyword allowed_headers: iterable of headers to allow.
        :keyword allowed_methods: iterable of HTTP methods to allow.
        :keyword allowed_regexes: iterable of regexes to match against origin.
        """
        self.app = app
        self.allowed_netlocs = allowed_netlocs or tuple()
        self.allowed_hostnames = allowed_hostnames or tuple()
        self.allowed_regexes = allowed_regexes or tuple()
        # Precaclcuate these since they won't change per request
        self.allowed_methods = ', '.join(allowed_methods)
        self.allowed_headers = ', '.join(allowed_headers)
        self.header_string = ', '.join(self.allowed_headers)
        self.allowed_regexes = [re.compile(r) for r in self.allowed_regexes]

    def __call__(self, environ, start_response):
        """Filter for CORS."""
        if not webob:
            raise RuntimeError(
                "CORSMiddleware requires `webob` which was not could not be "
                "imported. If you want to use simpl.middleware.cors, run "
                "`pip install WebOb` or "
                "`pip install -r optional-requirements.txt`")
        request = webob.Request(environ)
        origin = request.headers.get('Origin')
        if origin:
            url = parse.urlparse(origin)
        if origin and (url.netloc in self.allowed_netlocs or
                       url.hostname in self.allowed_hostnames or
                       any(r.match(origin) for r in self.allowed_regexes)):
            start_response = self.start_response_callback(start_response,
                                                          origin)
            if environ['REQUEST_METHOD'] == 'OPTIONS':
                response = webob.Response()
                response.headerlist = [
                    ('Access-Control-Allow-Methods', self.allowed_methods),
                    ('Access-Control-Allow-Headers', self.allowed_headers),
                    ('Access-Control-Allow-Credentials', 'true'),
                ]
                return response(environ, start_response)
            environ['CORS_TRUSTED_ORIGIN'] = True
        elif origin:
            LOG.info("Unknown origin '%s'. Responding without CORS headers",
                     origin)
        return self.app(environ, start_response)

    @staticmethod
    def start_response_callback(start_response, origin):
        """Intercept upstream start_response and adds our headers."""
        def callback(status, headers, exc_info=None):
            """Add our headers to response using a closure."""
            headers.append(('Access-Control-Allow-Origin', origin))
            # Call upstream start_response
            start_response(status, headers, exc_info)
        return callback
