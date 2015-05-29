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

"""Simpl bottle-based server.

Runs with the following built-in middlewares by default:
    StripPathMiddleware:
        - strips/normalizes extra "/"s
    CORSMiddleware
        -

"""
import sys

from simpl.utils import import_me_maybe

bottle = import_me_maybe('bottle')
eventlet = import_me_maybe('eventlet')

_server_adapter = 'eventlet' if eventlet else 'wsgiref'


def run(app=None,
        server=_server_adapter,
        host='127.0.0.1',
        port=8080,
        interval=1,
        reloader=False,
        quiet=False,
        plugins=None,
        debug=None,
        **kwargs):
    """Start a server instance. This method blocks until the server terminates.

    :param app: WSGI application or target string supported by
           :func:`load_app`. (default: :func:`default_app`)
    :param server: Server adapter to use. See :data:`server_names` keys
           for valid names or pass a :class:`ServerAdapter` subclass.
           (default: `wsgiref`)
    :param host: Server address to bind to. Pass ``0.0.0.0`` to listens on
           all interfaces including the external one. (default: 127.0.0.1)
    :param port: Server port to bind to. Values below 1024 require root
           privileges. (default: 8080)
    :param reloader: Start auto-reloading server? (default: False)
    :param interval: Auto-reloader interval in seconds (default: 1)
    :param quiet: Suppress output to stdout and stderr? (default: False)
    :param options: Options passed to the server adapter.
     """
    return bottle.run(
        app=app,
        server=server,
        host=host,
        port=port,
        interval=interval,
        reloader=reloader,
        quiet=quiet,
        plugins=plugins,
        debug=debug,
        **kwargs)


if __name__ == '__main__':

    if not bottle:
        sys.exit()

    import argparse

    from simpl.utils import cli

    parser = cli.HelpfulParser(
        description=__doc__.splitlines()[0],
        epilog="\n".join(__doc__.splitlines()[1:]),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '--app', '-a',
        help=("WSGI application to load by name. "
              "Ex: package.module gets the module"
              "    package.module:name gets the variable 'name'"
              "    package.module.func() calls func() and gets the result")
    )
    parser.add_argument(
        '-s', default=_server_adapter,
        choices=bottle.server_names.keys(),
        dest='server',
        help="Server backend. Defaults to 'eventlet' if available."
    )
    parser.add_argument(
        '--host', '-i', default='127.0.0.1',
        help=('Server address to bind to. Pass 0.0.0.0 to listen on '
              'all interfaces including the external one. ')
    )
    parser.add_argument(
        '--port', '-p', default='8080',
        help='Server port to bind to. Values below 1024 require '
              'root priveleges.'
    )
    parser.add_argument('--reloader', '-r', action='store_true',
                        default=False, help="Start auto-reloading server?")

    # TODO(sam): add quiet, loglevel options??

    args, extras = parser.parse_known_args()
    bottle_kwargs = {key.replace('-', '_'): val
                     for key, val in zip(extras[::2], extras[1::2])}
    run(app=args.app, server=args.server, host=args.host,
        port=args.port, reloader=args.reloader, **bottle_kwargs)
