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
import tempfile
import shutil
import subprocess
import unittest
import uuid
import warnings

import mock
import webtest

from checkmate.common import git as common_git
from checkmate.common import backports
from checkmate import exceptions as cmexc
from checkmate.common.git import manager
from checkmate.common.git import middleware

TEST_PATH = '/tmp/checkmate/test'


class MockWsgiApp(object):
    """Mock class for WsgiApp."""
    def __init__(self):
        pass

    def __call__(self, env, start_response):
        assert False, "No calls should get to backend"


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



class TestGitCommands(unittest.TestCase):

    init_success = "initialized empty git repository"

    def setUp(self):
        prefix = "%s-" % __name__
        self.tempdir = backports.TemporaryDirectory(prefix=prefix)
        self.repo = common_git.GitRepo(self.tempdir.name)
        self.tempdir_b = backports.TemporaryDirectory(prefix=prefix)
        self.repo_b = common_git.GitRepo(self.tempdir_b.name)

    def tearDown(self):
        self.tempdir.cleanup()
        self.tempdir_b.cleanup()

    def test_initialize_repository(self):
        output = self.repo.init()
        self.assertIn(
            self.init_success, output['stdout'].lower())

    def test_init_and_clone_from(self):
        output = self.repo.init()
        self.assertIn(self.init_success, output['stdout'].lower())
        output = self.repo_b.clone(self.repo.repo_dir)
        msg = "cloning into '%s'" % self.repo_b.repo_dir.lower()
        self.assertIn(msg, output['stdout'].lower())

    def test_tag(self):
        test_tag = 'thanks_for_the_tag'
        self.repo.init()
        # needs a commit, o/w fails: "No such ref: HEAD"
        self.repo.commit(stage=False)
        self.repo.tag(test_tag)
        tag_list = self.repo.list_tags()
        self.assertIn(test_tag, tag_list)

    def test_clone_brings_tags(self):
        cloned_tag = 'tag_from_repo_A_for_repo_B'
        self.repo.init()
        self.repo.commit(stage=False)
        self.repo.tag(cloned_tag)

        self.repo_b.clone(self.repo.repo_dir)
        tag_list = self.repo_b.list_tags()
        self.assertIn(cloned_tag, tag_list)

    def test_duplicate_tag_updates(self):
        test_tag = 'duplicate_me'
        self.repo.init()
        # needs a commit, otherwise fails w/ "No such ref: HEAD"
        self.repo.commit(stage=False)
        self.repo.tag(test_tag)
        self.repo.commit(stage=False)
        output = self.repo.tag(test_tag)
        msg = "updated tag '%s'" % test_tag
        self.assertIn(msg.lower(), output['stdout'].lower())

    def test_duplicate_tag_fails_without_force(self):
        test_tag = 'duplicate_me'
        self.repo.init()
        # needs a commit, o/w fails: "No such ref: HEAD"
        self.repo.commit(stage=False)
        self.repo.tag(test_tag)
        self.assertRaises(
            cmexc.CheckmateCalledProcessError, self.repo.tag,
            test_tag, force=False)

    def test_tag_with_spaces_fails(self):
        test_tag = 'x k c d'
        self.repo.init()
        # needs a commit, o/w fails: "No such ref: HEAD"
        self.repo.commit(stage=False)
        self.assertRaises(
            cmexc.CheckmateCalledProcessError, self.repo.tag,
            test_tag)

    def test_annotated_tag(self):
        test_tag = 'v2.0.0'
        test_message = "2 is better than 1"
        self.repo.init()
        self.repo.commit(stage=False)
        self.repo.tag(test_tag, message=test_message)
        tags = self.repo.list_tags(with_messages=False)
        self.assertIn('v2.0.0', tags)
        tags = self.repo.list_tags(with_messages=True)
        self.assertIn((test_tag, test_message), tags)

    def test_commit_automatically_stages(self):
        self.repo.init()
        temp = tempfile.NamedTemporaryFile(
            dir=self.repo.repo_dir, suffix='.cmtest')
        temp.write("calmer than you are")
        temp.flush()
        msg = "1 file changed"
        output = self.repo.commit(message="dudeism")
        self.assertIn(msg.lower(), output['stdout'].lower())
        self.assertIn('dudeism', output['stdout'].lower())

    def test_commit_with_long_message(self):
        self.repo.init()
        self.repo.commit(stage=False)
        hash_before = self.repo.head
        self.repo.commit(message='fix(api): dont implode', stage=False)
        hash_after = self.repo.head
        self.assertNotEqual(hash_before, hash_after)

    def test_checkout(self):
        self.repo.init()
        self.repo.commit(stage=False)
        hash_before = self.repo.head
        self.repo.tag('tag_before_changes')

        temp = tempfile.NamedTemporaryFile(
            dir=self.repo.repo_dir, suffix='.cmtest')
        temp.file.write("calmer than you are")
        self.repo.commit(message="dudeism")
        hash_after = self.repo.head
        self.repo.tag('tag_after_changes')
        self.repo.checkout('tag_before_changes')
        self.assertNotEqual(hash_before, hash_after)
        self.assertEqual(self.repo.head, hash_before)
        self.repo.checkout('tag_after_changes')
        self.assertEqual(self.repo.head, hash_after)

    def test_fetch_checkout_remote(self):
        cloned_tag = 'tag_from_repo_A_for_repo_B'
        self.repo.init()
        self.repo.commit(stage=False)
        self.repo.tag(cloned_tag)

        # init, fetch, and checkout instead of cloning
        self.repo_b.init()
        self.repo_b.fetch(remote=self.repo.repo_dir, refspec=cloned_tag)
        self.repo_b.checkout(cloned_tag)
        tags = self.repo_b.list_tags()
        self.assertIn(cloned_tag, tags)
        self.assertEqual(self.repo.head, self.repo_b.head)

    def test_fetch_checkout_remote_commit(self):
        self.repo.init()
        self.repo.commit(stage=False)
        new_commit_hash = self.repo.head

        # init, fetch, and checkout instead of cloning
        self.repo_b.init()
        # NOTE(larsbutler): For a full explanation of why we need to add a
        # `commit` here before fetching and checking out, see
        # `checkmate.common.git.check_git_version`.
        self.repo_b.commit(stage=False)
        self.repo_b.fetch(remote=self.repo.repo_dir)
        self.repo_b.checkout(new_commit_hash)
        self.assertEqual(self.repo.head, self.repo_b.head)

    def test_pull_remote(self):
        self.repo.init()
        self.repo.commit(stage=False)
        self.repo.tag('tag_to_pull')
        new_commit_hash = self.repo.head

        # init and pull instead of cloning
        self.repo_b.init()
        # needs a commit, o/w fails: "Cannot update the ref 'HEAD'."
        self.repo_b.commit(stage=False)
        self.repo_b.pull(remote=self.repo.repo_dir, ref='tag_to_pull')
        self.repo_b.checkout('FETCH_HEAD')
        self.assertEqual(self.repo.head, self.repo_b.head)


class TestGitVersion(unittest.TestCase):

    def test_check_git_version_no_git(self):
        # Check that a warning is raised if git isn't installed.
        with mock.patch('checkmate.common.git.git_version') as gv:
            gv.return_value = dict(returncode=127, stdout='git: command not found')
            with warnings.catch_warnings(record=True) as w:
                common_git.check_git_version()
                [warning] = w
                self.assertEqual("Git does not appear to be installed!",
                                 warning.message.message)

    def test_check_git_version_old(self):
        # Check that a warning is raised if the installed git version is older
        # than recommended.
        with mock.patch('checkmate.common.git.git_version') as gv:
            gv.return_value = dict(returncode=0, stdout='git version 1.8.5.6')
            with warnings.catch_warnings(record=True) as w:
                common_git.check_git_version()
                [warning] = w
                self.assertEqual(
                    "Git version 1.8.5.6 found. 1.9 or greater is recommended",
                    warning.message.message)


if __name__ == '__main__':
    from checkmate import test
    test.run_with_params()