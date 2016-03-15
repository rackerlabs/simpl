# Copyright 2015 Rackspace US, Inc.
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

import eventlet
eventlet.monkey_patch()

import logging
import multiprocessing
import os
import pprint
import random
import socket
import string
import subprocess
import sys
import threading
import unittest

try:
    import queue
except ImportError:
    import Queue as queue

import requests

import simpl

LOG = logging.getLogger(__name__)


def get_free_port(host):
    sock = socket.socket()
    sock.bind((host, 0))
    port = sock.getsockname()[1]
    sock.close()
    del sock
    return port


def _queued_output(out):
    """Use a separate process to read server stdout into a queue.

    Returns the queue object. Use get() or get_nowait() to read
    from it.
    """
    def _enqueue_output(_out, _queue):
        for line in _out:
            _queue.put(line)
    output_queue = multiprocessing.Queue()
    # I tried a Thread, it was blocking the main thread because
    # of GIL I guess. This made me very confused.
    process = multiprocessing.Process(
        target=_enqueue_output, args=(out, output_queue))
    process.daemon = True
    process.start()
    return output_queue


class TestServerFunctional(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.host = '127.0.0.1'
        cls.port = get_free_port(cls.host)
        cls.url = 'http://%s:%s' % (cls.host, cls.port)
        cls.test_env = ''.join(random.sample(string.hexdigits, 22))
        # Using simpl.__path__ instead of just `simpl server`
        # to ensure we don't get a rogue binary.
        # Use sys.executable to ensure we run the server using
        # the exact same python interpreter as this test is using.
        exe = os.path.join(simpl.__path__[0], 'server.py')
        assert os.path.isfile(exe)
        argv = [
            sys.executable,
            exe,
            '--host', cls.host,
            '--port', str(cls.port),
            '--server', 'eventlet',
            '--verbose',
            '--debug',
            '--environment', cls.test_env,
            '--no-reloader',
        ]

        server_started = "Listening on {url}/".format(url=cls.url)

        # ensure a hard-coded os.environ when testing!
        # Without the unbuffered flag this doesn't
        # work in > Python 3.
        _env = {
            'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONUNBUFFERED': '1',
        }
        # bufsize=1 means line buffered.
        # universal_newlines=True makes stdout text and not bytes
        cls.server = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            env=_env,
        )

        cls._timeout = 5
        startup_timeout = threading.Timer(cls._timeout, cls.server.kill)
        startup_timeout.daemon = True
        startup_timeout.start()

        cls.non_blocking_read_queue = _queued_output(cls.server.stdout)
        # cls.server.poll() will return -9 if Timer kill() sends SIGKILL
        while cls.server.poll() is None:
            try:
                line = cls.non_blocking_read_queue.get_nowait()
            except queue.Empty:
                continue
            else:
                LOG.debug("Test simpl server STDOUT: %s", line)
                if server_started in line:
                    startup_timeout.cancel()
                    LOG.info("simpl server started successfully!")
                    break

    def setUp(self):
        """Ensure that the server started."""
        code = self.server.poll()
        # if code is None: server running.
        # if code is 0, server exited for some reason.
        if code:
            if code == -9:
                self.fail("Failed to start simpl server within "
                          "the %s second timeout!" % self._timeout)
            else:
                self.fail("Failed to start test simpl server process! "
                          "Exit code: %s" % code)
        if code == 0:
            self.fail("Server died for some reason with a 0 exit code.")

        self.session = requests.session()
        # Set up retries to not fail during server startup delay
        retry = requests.packages.urllib3.util.Retry(
            total=5, backoff_factor=0.2)
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        self.session.mount(self.url, adapter)

    @classmethod
    def tearDownClass(cls):
        while not cls.non_blocking_read_queue.empty():
            line = cls.non_blocking_read_queue.get_nowait()
            LOG.debug("POST-MORTEM test simpl server STDOUT: %s", line)
        try:
            cls.server.kill()
        except OSError:
            pass

    def _check_response(self, response):
        """Check for 500s and debug-tracebacks."""
        if response.status_code == 500:
            req = response.request
            try:
                body = response.json()
                if 'traceback' in body:
                    msg = ('Traceback from test simpl server '
                           'when calling {m} {p}\n{tb}')
                    self.fail(
                        msg.format(m=req.method,
                                   p=req.path_url,
                                   tb=body['traceback'])  # fail
                    )
                else:
                    self.fail(pprint.pformat(body, indent=2))
            except (TypeError, ValueError):
                pass

    def test_simpl_version(self):
        vers = self.session.get('{}/_simpl'.format(self.url))
        self._check_response(vers)
        expected = {
            'version': simpl.__version__,
            'url': simpl.__url__,
        }
        self.assertEqual(expected, vers.json())

    def test_not_found(self):
        response = self.session.get('{}/i/dont/exist'.format(self.url))
        self._check_response(response)
        self.assertEqual(404, response.status_code)


if __name__ == '__main__':
    opts = {}
    if any(v in ' '.join(sys.argv) for v in ['--verbose', '-v']):
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
        opts['verbosity'] = 2
    unittest.main(**opts)
