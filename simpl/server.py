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

from __future__ import print_function

import copy
import logging
import operator
import os
import sys
import textwrap

import bottle
import six  # pylint: disable=wrong-import-order

import simpl

from simpl import config
from simpl.utils import cli as cli_utils

LOG = logging.getLogger(__name__)


def _fill(text):
    """Make a pretty text block."""
    return textwrap.fill(text, 50)


OPTIONS = [
    config.Option(
        '--app', '-a',
        help=("WSGI application to load by name.\n"
              "Ex: package.module gets the module\n"
              "    package.module:name gets the variable 'name'\n"
              "    package.module.func() calls func() and gets the result"),
        group='Server Options',
    ),
    config.Option(
        '--host',
        help='Server address to bind to.',
        default='127.0.0.1',
        group='Server Options',
    ),
    config.Option(
        '--port', '-p',
        help='Server port to bind to.',
        type=int,
        default=8080,
        group='Server Options',
    ),
    config.Option(
        '--server', '-s',
        help=('Server adapter to use. To see more, run:\n'
              '`python -c "import bottle;print('
              'bottle.server_names.keys())"`\n'),
        default='xtornado',
        group='Server Options',
    ),
    config.OPTIONS['debug'],
    config.OPTIONS['quiet'],
    config.Option(
        '--no-reloader',
        default=True,
        dest='reloader',
        action='store_false',
        help=_fill(
            'Disable bottle auto-reloading server, which automatically '
            'restarts the server when file changes are detected. Note: '
            'some server adapters, such as eventlet, do not support '
            'auto-reloading.'),
        group='Server Options',
    ),
    config.Option(
        '--interval', '-i',
        help='Auto-reloader interval in seconds',
        type=int,
        default=1,
        group='Server Options',
    ),
    config.Option(
        '--adapter-options', '-o',
        help=(
            "Key-value pairs separated by '=' to be passed to \n"
            "the underlying server adapter, e.g. XEventletServer, \n"
            "and are mapped to the adapter's self.options \n"
            "instance attribute. Example usage:\n"
            "  simpl server -s xeventlet -o keyfile=~/mykey ciphers=GOST94\n"),
        nargs='*',
        type=cli_utils.kwarg,
        group='Server Options',
    ),
]

CONFIG = config.Config(
    prog='simpl_server',
    options=OPTIONS,
    argparser_class=cli_utils.HelpfulParser,
    formatter_class=cli_utils.SimplHelpFormatter
)


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


def attach_parser(subparser):
    """Given a subparser, build and return the server parser."""
    return subparser.add_parser(
        'server',
        help='Run a bottle based server',
        parents=[
            CONFIG.build_parser(
                add_help=False,
                # might need conflict_handler
            ),
        ],
    )


def fmt_pairs(obj, indent=4, sort_key=None):
    """Format and sort a list of pairs, usually for printing.

    If sort_key is provided, the value will be passed as the
    'key' keyword argument of the sorted() function when
    sorting the items. This allows for the input such as
    [('A', 3), ('B', 5), ('Z', 1)] to be sorted by the ints
    but formatted like so:

        l = [('A', 3), ('B', 5), ('Z', 1)]
        print(fmt_pairs(l, sort_key=lambda x: x[1]))

            Z 1
            A 3
            B 5
        where the default behavior would be:

        print(fmt_pairs(l))

            A 3
            B 5
            Z 1
    """
    lengths = [len(x[0]) for x in obj]
    if not lengths:
        return ''
    longest = max(lengths)
    obj = sorted(obj, key=sort_key)
    formatter = '%s{: <%d} {}' % (' ' * indent, longest)
    string = '\n'.join([formatter.format(k, v) for k, v in obj])
    return string


def fmt_routes(bottle_app):
    """Return a pretty formatted string of the list of routes."""
    routes = [(r.method, r.rule) for r in bottle_app.routes]
    if not routes:
        return
    string = 'Routes:\n'
    string += fmt_pairs(routes, sort_key=operator.itemgetter(1))
    return string


def _version_callback():
    """Return a dict of simpl version info."""
    return {
        'version': simpl.__version__,
        'url': simpl.__url__,
    }


def build_application(conf):
    """Do some setup and return the wsgi app."""
    if isinstance(conf.adapter_options, list):
        conf['adapter_options'] = {key: val for _dict in conf.adapter_options
                                   for key, val in _dict.items()}
    elif conf.adapter_options is None:
        conf['adapter_options'] = {}
    else:
        conf['adapter_options'] = copy.copy(conf.adapter_options)

    # get wsgi app the same way bottle does if it receives a string.
    conf['app'] = conf.app or bottle.default_app()
    if isinstance(conf.app, six.string_types):
        conf['app'] = bottle.load_app(conf.app)

    def _find_bottle_app(_app):
        """Lookup the underlying Bottle() instance."""
        while hasattr(_app, 'app'):
            if isinstance(_app, bottle.Bottle):
                break
            _app = _app.app
        assert isinstance(_app, bottle.Bottle), 'Could not find Bottle app.'
        return _app

    bottle_app = _find_bottle_app(conf.app)
    bottle_app.route(
        path='/_simpl', method='GET', callback=_version_callback)

    def _show_routes():
        """Conditionally print the app's routes."""
        if conf.app and not conf.quiet:
            if conf.reloader and os.getenv('BOTTLE_CHILD'):
                LOG.info("Running bottle server with reloader.")
            elif not conf.reloader:
                pass
            else:
                return
            routes = fmt_routes(bottle_app)
            if routes:
                    print('\n{}'.format(routes), end='\n\n')
    _show_routes()
    return conf.app


def run(conf, build_app=True):
    """Run server based on this configuration.

    If build_app is True, simpl will use your config to build
    and configure your wsgi application. If you have built and
    configured your application (conf.app) already, set build_app
    to false.

    Expects configuration options defined in server.OPTIONS
    """
    if build_app:
        # The following sets conf.app
        build_application(conf)
    # waiting for https://github.com/bottlepy/bottle/pull/783
    if conf.app and (os.getcwd() not in sys.path):
        sys.path.append(os.getcwd())
    return bottle.run(
        app=conf.app,
        server=conf.server,
        host=conf.host,
        port=conf.port,
        interval=conf.interval,
        reloader=conf.reloader,
        quiet=conf.quiet,
        debug=conf.debug,
        **conf.adapter_options
    )


def main(argv=None):
    """Command line entry point for server, runs based on parsed CONFIG."""
    CONFIG.parse(argv=argv)
    return run(CONFIG)


if __name__ == '__main__':
    main()
