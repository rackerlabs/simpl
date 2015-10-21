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

"""Context WSGI Middleware.

Creates a context for the WSGI call and adds the following to the context:
- transaction_id: a UUID to identify the call (this can be passed in the
        context to remote workers)
- base_url: the URL of the incoming call (overrideable)

The transaction id is returned in responses as an X-Transaction-Id header.

Example usage:

    # Disable all CORS checks:
    import bottle
    from simpl.middleware import context

    app = bottle.default_app()
    chain = context.ContextMiddleware(app, override_url="https://my_app.io")
    bottle.run(app=chain)
"""

import contextlib
import logging
import uuid

from simpl import threadlocal

LOG = logging.getLogger(__name__)


class ContextMiddleware(object):  # pylint: disable=R0903

    """Adds a call context to the call environ which holds call data."""

    def __init__(self, app, override_url=None):
        """Add a call context to the call environ which holds authn+z data."""
        self.app = app
        self.override_url = override_url

    def get_url(self, environ):
        """Return the base URL."""
        if self.override_url:
            url = self.override_url
        else:
            # PEP333: wsgi.url_scheme, HTTP_HOST, SERVER_NAME, and SERVER_PORT
            # can be used to reconstruct a request's complete URL

            # Much of the following is copied from bottle.py
            http = (environ.get('HTTP_X_FORWARDED_PROTO') or
                    environ.get('wsgi.url_scheme', 'http'))
            host = (environ.get('HTTP_X_FORWARDED_HOST') or
                    environ.get('HTTP_HOST'))
            if not host:
                # HTTP 1.1 requires a Host-header. This is for HTTP/1.0
                # clients.
                host = environ.get('SERVER_NAME', '127.0.0.1')
                port = environ.get('SERVER_PORT')
                if port and port != ('80' if http == 'http' else '443'):
                    host += ':' + port
            url = "%s://%s" % (http, host)
        return url

    def populate_context(self, context, environ):
        """Set initial context values."""
        url = self.get_url(environ)
        context['base_url'] = url
        transaction_id = uuid.uuid4().hex
        context['transaction_id'] = transaction_id
        LOG.debug("Context created: base_url=%s, tid=%s", url, transaction_id)

    def __call__(self, environ, start_response):
        """Handle WSGI Request."""
        with clear(threadlocal.default()) as context:
            assert context == {}, "New thread context was not empty"
            self.populate_context(context, environ)
            environ['context'] = context
            resp = self.app(
                environ,
                self.start_response_callback(start_response,
                                             context['transaction_id']))
            return resp

    @staticmethod
    def start_response_callback(start_response, transaction_id):
        """Intercept upstream start_response and adds our headers."""
        def callback(status, headers, exc_info=None):
            """Add our headers to response using a closure."""
            headers.append(('X-Transaction-Id', transaction_id))
            # Call upstream start_response
            start_response(status, headers, exc_info)
        return callback


@contextlib.contextmanager
def clear(local_dict):
    """Context manager that clears objects when done."""
    try:
        yield local_dict
    finally:
        LOG.debug("Clearing local context %s", id(local_dict))
        local_dict.clear()
