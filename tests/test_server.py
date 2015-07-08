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

"""Test :mod:`simpl.server`."""

import os
import signal
import socket
import unittest

import bottle
import mock
import requests

from simpl import server


class TestServer(unittest.TestCase):

    def test_xtornado_registered(self):
        self.assertIs(bottle.server_names['xtornado'], server.XTornadoServer)

    def test_xeventlet_registered(self):
        self.assertIs(bottle.server_names['xeventlet'], server.XEventletServer)

    def test_xtornado(self):
        resp = run_server('xtornado')
        self.assertTrue(resp.ok)
        self.assertEqual(resp.content, b'<b>Hello xtornado</b>!')

    def test_xeventlet(self):
        resp = run_server('xeventlet')
        self.assertTrue(resp.ok)
        self.assertEqual(resp.content, b'<b>Hello xeventlet</b>!')


class TestEventletLogger(unittest.TestCase):

    def test_wsgi_entry(self):
        """wsgi event should be written to debug log only."""
        log = mock.Mock()
        access_log = mock.Mock()
        instance = server.EventletLogFilter(log, access_log=access_log)
        instance.write("wsgi exiting\n")
        log.debug.assert_called_once_with("wsgi exiting")
        access_log.write.assert_not_called()

    def test_thread_entry(self):
        """Thread event should be written to debug log only."""
        log = mock.Mock()
        access_log = mock.Mock()
        instance = server.EventletLogFilter(log, access_log=access_log)
        instance.write("(123) accepted ('127.0.0.1', 678)\n")
        log.debug.assert_called_once_with("(123) accepted ('127.0.0.1', 678)")
        access_log.write.assert_not_called()

    def test_call_entry(self):
        """Callevent should be written to info and access logs."""
        log = mock.Mock()
        access_log = mock.Mock()
        instance = server.EventletLogFilter(log, access_log=access_log)
        entry = '127.0.0.1 - [07/Jul/2015] "GET / HTTP/1.1" 200'
        instance.write(entry + "\n")
        log.info.assert_called_once_with(entry)
        access_log.write.assert_called_once_with(entry + "\n")


def get_free_port(host="localhost"):
    """Get a free port on the machine."""
    temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    temp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    temp_sock.bind((host, 0))
    port = temp_sock.getsockname()[1]
    temp_sock.close()
    del temp_sock
    return port


@bottle.route('/hello/<name>')
def index(name):
    """Test HTTP responder."""
    if name == 'close':
        # Allows us to easily tell the child process to exit
        os._exit(0)
    return bottle.template('<b>Hello {{name}}</b>!', name=name)


def wait_for_ready_message(read_file):
    """Wait for bottle server to declare it is ready."""
    while True:
        txt = read_file.readline()
        if txt == '':
            assert False, "Ready signal not seen from %s server" % server
        if 'Hit Ctrl-C to quit' in txt:
            break


def run_server(server):
    """Start bottle server in a fork.

    Sets up a pipe for the child process to talk back to the parent.
    """
    pipe_out, pipe_in = os.pipe()
    port = get_free_port()
    pid = os.fork()  # fork a child to run the server in
    if pid:
        # we are the parent
        os.close(pipe_in)  # close the copy of the pipe write descriptor
        read_file = os.fdopen(pipe_out)  # turn handle into a file object

        wait_for_ready_message(read_file)

        # Set up retries to not fail during server startup delay
        retry = requests.packages.urllib3.util.Retry(
            total=5, backoff_factor=0.2)
        session = requests.Session()
        session.mount("http://",
                      requests.adapters.HTTPAdapter(max_retries=retry))
        try:
            return session.get('http://127.0.0.1:%s/hello/%s' % (port, server))
        finally:
            try:
                # Try gracefull shutdown from inside child process
                requests.get('http://127.0.0.1:%s/hello/close' % port)
            except Exception:
                # Fall back to hard shutdown
                os.kill(pid, signal.SIGTERM)
            os.waitpid(pid, 0)
            read_file.close()
        assert False, "Failed to start or connect to server '%s'" % server
    else:
        # we are the child
        os.close(pipe_out)  # close our copy of the read descriptor

        # hijack bottle's stdout and stderr and send them to the pipe
        pipe_in = os.fdopen(pipe_in, 'w')

        def flushout(text):
            """Write out text immediately (no caching)."""
            pipe_in.write(text)
            pipe_in.flush()
        bottle._stderr = flushout
        bottle._stdout = flushout

        # Start server
        log = None
        if server == 'xeventlet':
            import eventlet
            eventlet.monkey_patch()
            log = pipe_in  # capture eventlet messages too
        bottle.run(port=port, host='127.0.0.1', server=server,
                   autoreloader=False, log=log)

if __name__ == '__main__':
    unittest.main()
