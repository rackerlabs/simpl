# pylint: disable=R0903,R0904
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

"""Tests for git integration (general)."""
import base64
import json
import os
import shutil
import subprocess
import sys
import unittest
import uuid

import mock
import webtest

from checkmate.common.git import manager
from checkmate.common.git import middleware


class MockWsgiApp(object):
    """Mock class for WsgiApp."""
    def __init__(self):
        pass

    def __call__(self, env, start_response):
        assert False, "No calls should get to backend"


def _start_response():
    """Mock for _start_response that does nothing."""
    pass


TEST_PATH = '/tmp/checkmate/test'


class TestCloneSimple(unittest.TestCase):
    def setUp(self):
        self.repo_id = uuid.uuid4().hex
        self.repo_path = os.path.join(TEST_PATH, self.repo_id)
        os.makedirs(self.repo_path)
        manager.init_deployment_repo(self.repo_path)
        self.fake_auth = 'https://identity-internal/path'
        os.environ['CHECKMATE_AUTH_ENDPOINTS'] = json.dumps([
            {'uri': self.fake_auth}])

        self.root_app = MockWsgiApp()
        self.middleware = middleware.GitMiddleware(self.root_app, TEST_PATH)
        self.app = webtest.TestApp(self.middleware)

    def tearDown(self):
        shutil.rmtree(self.repo_path)

    def test_no_auth(self):
        res = self.app.get(
            '/T1/deployments/DEP01.git/info/refs?service=git-upload-pack',
            expect_errors=True
        )
        self.assertEqual(res.status, '401 Unauthorized')

    @mock.patch.object(middleware, '_auth_racker')
    def test_bad_auth(self, mock_auth):
        mock_auth.return_value = None
        encoded_auth = base64.b64encode('%s:%s' % ("john", "wrong"))
        res = self.app.get(
            '/T1/deployments/DEP01.git/info/refs?service=git-upload-pack',
            headers={'Authorization': 'Basic %s' % encoded_auth},
            expect_errors=True
        )
        mock_auth.assert_called_with(self.fake_auth, "john", "wrong")
        self.assertEqual(res.status, '401 Unauthorized')

    @mock.patch.object(middleware, '_auth_racker')
    def test_bad_path(self, mock_auth):
        mock_auth.return_value = {'access': True}
        encoded_auth = base64.b64encode('%s:%s' % ("john", "secret"))
        res = self.app.get(
            '/T1/deployments/DEP01.git/info/refs?service=git-upload-pack',
            headers={'Authorization': 'Basic %s' % encoded_auth},
            expect_errors=True
        )
        mock_auth.assert_called_with(self.fake_auth, "john", "secret")
        self.assertEqual(res.status, '404 Not Found')

    def test_backend_clone_first_call(self):
        """GIT_CURL_VERBOSE=1
        git clone http://localhost:8080/557366/deployments/08af2c9e979e4c0c9e2
        561791a745794.git
        """
        os.environ['REQUEST_METHOD'] = 'GET'
        os.environ['GIT_PROJECT_ROOT'] = self.repo_path
        os.environ['PATH_INFO'] = '/info/refs'
        os.environ['GIT_HTTP_EXPORT_ALL'] = '1'
        subprocess.check_output(['git', 'http-backend'])

    @unittest.skip('Unable to get this to work with TestApp')
    def test_clone(self):
        res = self.app.get(
            '/T1/deployments/%s.git/info/refs?service=git-upload-pack' %
            self.repo_id,
        )
        self.assertEqual(res.status, '200 OK')
        self.assertEqual(res.content_type, 'text/plain')
        self.assertIsNone(res.body)


if __name__ == '__main__':
    from checkmate import test as cmtest
    cmtest.run_with_params(sys.argv[:])
