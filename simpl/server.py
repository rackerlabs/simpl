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

"""Bottle Server Module."""

import logging
import os

import bottle

LOG = logging.getLogger(__name__)


class EventletLogFilter(object):  # pylint: disable=R0903

    """Receives eventlet log.write() calls and routes them.

    Thread and WSGI messages only get written in debug mode. Eventlet writes
    these out starting with a thread id in parens or "wsgi" messages:
    - "(46722) wsgi starting up on http://127.0.0.1:8080/"
    - "(47001) accepted ('127.0.0.1', 53046)"
    - "wsgi exiting"

    All other calls are assumed to be apache log-style API calls and we want
    these written as INFO and to an access_log if provided.

    API calls are assumed to start with the IP address:
    - "127.0.0.1 - - [07/Jul/2015 16:16:31] "GET /version HTTP/1.1" 200 ..."

    An instance of this class can be passed in to a bottle.run command using
    the `log` keyword.
    """

    def __init__(self, log, access_log=None):
        """Initialize with config and optional access_log.

        :param log: logger instance (ex. logging.getLogger()).
        :keyword access_log: a file handle to an access log that should receive
            apache-style entries for each call and response.
        """
        self.log = log
        self.access_log = access_log

    def write(self, text):
        """Write to appropriate target."""
        if text:
            if text[0] in '(w':
                # write thread and wsgi messages to debug only
                self.log.debug(text[:-1])
                return
            if self.access_log:
                self.access_log.write(text)
            self.log.info(text[:-1])


class XEventletServer(bottle.ServerAdapter):

    r"""Eventlet Bottle Server Adapter with extensions.

    Supports SSL. Accepts additional tuning parameters:

    * `backlog` adjust the eventlet backlog parameter which is the maximum
      number of queued connections. Should be at least 1; the maximum
      value is system-dependent.
    * `family`: (default is 2) socket family, optional. See socket
      documentation for available families.
    * `**kwargs`: directly map to python's ssl.wrap_socket arguments from
      https://docs.python.org/2/library/ssl.html#ssl.wrap_socket and
      wsgi.server arguments from
      http://eventlet.net/doc/modules/wsgi.html#wsgi-wsgi-server

    To create a self-signed key and start the eventlet server using SSL::

      openssl genrsa -des3 -out server.orig.key 2048
      openssl rsa -in server.orig.key -out test.key
      openssl req -new -key test.key -out server.csr
      openssl x509 -req -days 365 -in server.csr -signkey test.key -out \
      test.crt

      bottle.run(server='eventlet', keyfile='test.key', certfile='test.crt')
    """

    def get_socket(self):
        """Create listener socket based on bottle server parameters."""
        import eventlet

        # Separate out socket.listen arguments
        socket_args = {}
        for arg in ('backlog', 'family'):
            try:
                socket_args[arg] = self.options.pop(arg)
            except KeyError:
                pass
        # Separate out wrap_ssl arguments
        ssl_args = {}
        for arg in ('keyfile', 'certfile', 'server_side', 'cert_reqs',
                    'ssl_version', 'ca_certs', 'do_handshake_on_connect',
                    'suppress_ragged_eofs', 'ciphers'):
            try:
                ssl_args[arg] = self.options.pop(arg)
            except KeyError:
                pass
        address = (self.host, self.port)
        try:
            sock = eventlet.listen(address, **socket_args)
        except TypeError:
            # Fallback, if we have old version of eventlet
            sock = eventlet.listen(address)
        if ssl_args:
            sock = eventlet.wrap_ssl(sock, **ssl_args)
        return sock

    def run(self, handler):
        """Start bottle server."""
        import eventlet.patcher
        if not eventlet.patcher.is_monkey_patched(os):
            msg = ("%s requires eventlet.monkey_patch() (before "
                   "import)" % self.__class__.__name__)
            raise RuntimeError(msg)

        # Separate out wsgi.server arguments
        wsgi_args = {}
        for arg in ('log', 'environ', 'max_size', 'max_http_version',
                    'protocol', 'server_event', 'minimum_chunk_size',
                    'log_x_forwarded_for', 'custom_pool', 'keepalive',
                    'log_output', 'log_format', 'url_length_limit', 'debug',
                    'socket_timeout', 'capitalize_response_headers'):
            try:
                wsgi_args[arg] = self.options.pop(arg)
            except KeyError:
                pass
        if 'log_output' not in wsgi_args:
            wsgi_args['log_output'] = not self.quiet

        import eventlet.wsgi
        sock = self.options.pop('shared_socket', None) or self.get_socket()
        eventlet.wsgi.server(sock, handler, **wsgi_args)

    def __repr__(self):
        """Show class name, even if subclassed."""
        return self.__class__.__name__

bottle.server_names['xeventlet'] = XEventletServer


class XTornadoServer(bottle.ServerAdapter):  # pylint: disable=R0903

    """The Tornado Server Adapter with xheaders enabled."""

    def run(self, handler):
        """Start up the server."""
        import tornado.httpserver
        import tornado.ioloop
        import tornado.wsgi
        container = tornado.wsgi.WSGIContainer(handler)
        server = tornado.httpserver.HTTPServer(container, xheaders=True)
        server.listen(port=self.port, address=self.host)
        tornado.ioloop.IOLoop.instance().start()

bottle.server_names['xtornado'] = XTornadoServer
