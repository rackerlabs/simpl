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
#
# pylint: disable=R0903,R0904,C0111,C0103

"""Tests for git module."""

import os
import tempfile
import shutil
import unittest
import warnings

import mock

from simpl import IS_TRAVIS_CI_ENV
from simpl import exceptions
from simpl import git

TEST_GIT_USERNAME = 'simpl_git_test_user'


def _configure_test_user(gitrepo):

    email = '%s@%s.test' % (TEST_GIT_USERNAME, TEST_GIT_USERNAME)
    gitrepo.run_command('git config --local user.name %s' % TEST_GIT_USERNAME)
    gitrepo.run_command('git config --local user.email %s' % email)


class TestGitBase(unittest.TestCase):

    def new_repo(self):
        tmpd = self.create_tempdir()
        repo = git.GitRepo.init(tmpd)
        _configure_test_user(repo)
        repo.commit(message='Initial commit', stage=False, amend=False)
        _configure_test_user(repo)
        return repo

    def create_tempdir(self):
        prefix = "%s-" % '-'.join(__file__.split(os.sep)[-3:])
        new = tempfile.mkdtemp(prefix=prefix)
        self.tempdirs.append(new)
        return new

    def setUp(self):
        self.tempdirs = []
        self.repo = self.new_repo()
        self.repo_b = self.new_repo()

    def tearDown(self):
        for tmpd in self.tempdirs:
            shutil.rmtree(tmpd)


class TestGitRepo(TestGitBase):

    def test_raises_enoent(self):
        td = '/i/dont/exist'
        with self.assertRaises(OSError) as err:
            repo = git.GitRepo(td)

    # `git rev-parse` always exits 0 on travis-ci for some reason
    # maybe because the directories are technically part of a repo
    @unittest.skipIf(IS_TRAVIS_CI_ENV, "travis-ci should skip this")
    def test_raises_not_repo(self):
        td = self.create_tempdir()
        with self.assertRaises(exceptions.SimplGitNotRepo):
            repo = git.GitRepo(td)

    # `git rev-parse` always exits 0 on travis-ci for some reason
    # maybe because the directories are technically part of a repo
    @unittest.skipIf(IS_TRAVIS_CI_ENV, "travis-ci should skip this")
    def test_is_not_git_repo(self):
        td = self.create_tempdir()
        self.assertFalse(git.is_git_repo(td))

    def test_gitrepo_init_temp(self):
        gr = git.GitRepo.init(temp=True)
        self.assertTrue(gr.temp)
        self.assertIn(tempfile.gettempdir(), gr.repo_dir)

    def test_gitrepo_init_no_initial_commit(self):
        gr = git.GitRepo.init(temp=True)
        with self.assertRaises(exceptions.SimplGitCommandError):
            current_commit = gr.head

    def test_no_origin_property(self):
        self.assertEqual(self.repo.origin, None)

    def test_origin_property(self):
        gr = self.new_repo()
        clone = git.GitRepo.clone(gr.repo_dir, temp=True)
        self.assertEqual(clone.origin, gr.repo_dir)

    def test_gitrepo_clone_temp(self):
        gr = self.new_repo()
        clone = git.GitRepo.clone(gr.repo_dir, temp=True)
        self.assertTrue(clone.temp)
        self.assertIn(tempfile.gettempdir(), clone.repo_dir)

    def test_initialize_repository(self):
        tmpd = self.create_tempdir()
        output = git.git_init(tmpd)
        self.assertIn("initialized empty git repository",
                      output.lower())

    def test_init_and_clone_from(self):
        repo_c_path = self.create_tempdir()
        output = git.git_clone(repo_c_path, self.repo.repo_dir)
        msg = "cloning into '%s'" % repo_c_path.lower()
        self.assertIn(msg, output.lower())

    def test_list_config(self):
        gr = self.new_repo()
        cfg = gr.list_config()
        self.assertIn('user.name', cfg)
        self.assertEqual(TEST_GIT_USERNAME, cfg['user.name'])
        self.assertIn('user.email', cfg)

    def test_ls(self):

        filename = 'afile.txt'
        gr = self.new_repo()
        tf = tempfile.NamedTemporaryFile(dir=gr.repo_dir, suffix=filename)
        fullname = os.path.split(tf.name)[-1]
        status = gr.status()
        self.assertIn(fullname, status)
        gr.add_all()
        gr.commit(message='a great file, dot text')
        files = gr.ls()
        self.assertEqual([fullname], files)
        more = gr.ls_tree()
        self.assertTrue(1, len(more))
        target = more[0]
        self.assertIn('object', target)
        self.assertIn('type', target)
        self.assertEqual(target['type'], 'blob')
        self.assertIn('mode', target)
        self.assertIn('file', target)
        self.assertEqual(target['file'], fullname)

    def test_run_command(self):

        output = self.repo.run_command(['git', '--help'])
        self.assertTrue(output)

    def test_list_refs(self):
        self.repo.tag('whatatag')
        refs = self.repo.list_refs()
        self.assertIn('HEAD', refs)
        self.assertIn('refs/tags/whatatag', refs)
        self.assertIn('refs/heads/master', refs)

    def test_resolve_branch_ref(self):

        branch = 'new_feature'
        self.repo.branch(branch, checkout=True)
        tf1 = tempfile.NamedTemporaryFile(dir=self.repo.repo_dir)
        self.repo.commit('added a tempfile', stage=True)
        feature_revision = self.repo.head
        # now go checkout something else...
        self.repo.checkout('master')
        nextrepo = git.GitRepo.clone(self.repo.repo_dir, temp=True)
        _configure_test_user(nextrepo)
        self.assertEqual(nextrepo.current_branch, 'master')
        self.assertNotEqual(nextrepo.head, feature_revision)
        feature_revision_nextrepo = nextrepo.remote_resolve_reference(
            branch)
        self.assertEqual(feature_revision_nextrepo, feature_revision)
        nextrepo.branch('new_feature', start_point=feature_revision,
                        checkout=True)
        self.assertTrue(nextrepo.head, feature_revision)

    def test_ls_remote(self):
        initial_hash = self.repo.head
        initial_ref = self.repo.current_branch
        nextrepo = git.GitRepo.clone(self.repo.repo_dir, temp=True)
        _configure_test_user(nextrepo)
        ls_remotes = nextrepo.ls_remote(refs=initial_ref)
        master_hash = ls_remotes['refs/heads/master']
        self.assertEqual(master_hash, initial_hash)
        # now change "upstream"
        self.repo.commit(message='just to change the hash')
        ls_remotes = nextrepo.ls_remote(refs=initial_ref)
        new_master_hash = ls_remotes['refs/heads/master']
        # the cloned repo does not have a copy of
        # new_master_hash at this point
        self.assertNotEqual(new_master_hash, master_hash)

        with self.assertRaises(exceptions.SimplGitCommandError):
            nextrepo.branch('new', start_point=new_master_hash,
                            checkout=True)

        nextrepo.fetch(tags=True)
        nextrepo.fetch(tags=False)
        # now the branch should work
        nextrepo.branch('new', start_point=new_master_hash, checkout=True)
        self.assertEqual(nextrepo.head, new_master_hash)

    def test_changing_remote_resolve_branch_reference(self):
        initial_hash = self.repo.head
        initial_ref = self.repo.current_branch
        nextrepo = git.GitRepo.clone(self.repo.repo_dir, temp=True)
        _configure_test_user(nextrepo)
        master_hash = nextrepo.remote_resolve_reference(initial_ref)
        self.assertEqual(master_hash, initial_hash)
        # now change "upstream"
        self.repo.commit(message='just to change the hash')
        new_master_hash = nextrepo.remote_resolve_reference(initial_ref)
        # the cloned repo does not have a copy of
        # new_master_hash at this point
        self.assertNotEqual(new_master_hash, master_hash)

        with self.assertRaises(exceptions.SimplGitCommandError):
            nextrepo.checkout(new_master_hash, branch='new')

        nextrepo.fetch(tags=True)
        nextrepo.fetch(tags=False)
        # now the branch should work
        nextrepo.checkout(new_master_hash, branch='new')
        self.assertEqual(nextrepo.head, new_master_hash)

    def test_repr(self):
        rpr = '%r' % self.repo
        expected = '<Simpl GitRepo (tmp) {} at {}>'.format(
            self.repo.repo_dir, hex(id(self.repo)))
        self.assertEqual(rpr, expected)

    def test_remote_resolve_fails(self):
        gr = git.GitRepo.clone(self.repo.repo_dir, temp=True)
        revision = gr.remote_resolve_reference('notreal')
        self.assertIsNone(revision)

    def test_remote_resolve_tag_reference(self):
        tagname = 'lizard'
        self.repo.tag(tagname)
        gr = git.GitRepo.clone(self.repo.repo_dir, temp=True)
        revision = gr.remote_resolve_reference(tagname)
        self.assertEqual(self.repo.head, revision)

    def test_changing_remote_resolve_tag_reference(self):
        gr = git.GitRepo.clone(self.repo.repo_dir, temp=True)
        self.repo.commit(message='change the hash')
        tagname = 'lizard'
        self.repo.tag(tagname)
        revision = gr.remote_resolve_reference(tagname)
        with self.assertRaises(exceptions.SimplGitCommandError):
            gr.checkout(revision, branch='new')
        gr.fetch(tags=True)
        gr.fetch(tags=False)
        # now the branch should work
        gr.checkout(revision, branch='new')
        self.assertEqual(gr.head, revision)

    def test_branch(self):
        test_branch = 'thanks_for_the_branch'
        self.repo.branch(test_branch)
        branch_list = self.repo.list_branches()
        branchnames = [b['branch'] for b in branch_list]
        self.assertIn(test_branch, branchnames)

    def test_clone_brings_branches(self):
        cloned_branch = 'branch_from_repo_A_for_repo_B'
        self.repo.branch(cloned_branch)

        repo_c_path = self.create_tempdir()
        repo_c = git.GitRepo.clone(self.repo.repo_dir, repo_c_path)

        branch_list = repo_c.list_branches()
        branchnames = [b['branch'] for b in branch_list]
        self.assertIn('remotes/origin/%s' % cloned_branch, branchnames)

    def test_list_branches_detached_head_state(self):
        tf1 = tempfile.NamedTemporaryFile(dir=self.repo.repo_dir)
        out1 = self.repo.run_command(
            ['git', 'stash', 'save', '-u', 'stash message'])
        out2 = self.repo.checkout('stash@{0}')
        branches = self.repo.list_branches()
        for b in branches:
            if b['commit'] == self.repo.head:
                selected = b
                break
        else:
            self.fail("Could not find branch with current commit.")
        self.assertEqual(selected['commit'], self.repo.head)
        self.assertEqual(selected['message'], 'On master: stash message')
        try:
            fmtr = {'cmt': self.repo.head[:7]}
            # all but very new versions of git use this message
            self.assertEqual(
                selected['branch'], '(detached from {cmt})'.format(**fmtr))
        except AssertionError as e:
            # newer versions of git use this message
            self.assertEqual(
                selected['branch'], '(HEAD detached at {cmt})'.format(**fmtr))

    def test_list_remotes(self):

        gr = git.GitRepo.clone(self.repo.repo_dir, temp=True)
        remotes = gr.list_remotes()
        expected = {
            'cmd': '(fetch)',
            'name': 'origin',
            'location': self.repo.repo_dir,
        }
        self.assertIn(expected, remotes)

    def test_duplicate_branch_fails_without_force(self):
        test_branch = 'duplicate_me'
        self.repo.branch(test_branch)
        self.assertRaises(
            exceptions.SimplGitCommandError, self.repo.branch,
            test_branch, force=False)
        self.repo.branch(test_branch, force=True)

    def test_branch_with_spaces_fails(self):
        test_branch = 'x k c d'
        self.assertRaises(
            exceptions.SimplGitCommandError, self.repo.branch, test_branch)

    def test_tag(self):
        test_tag = 'thanks_for_the_tag'
        self.repo.tag(test_tag)
        tag_list = self.repo.list_tags()
        self.assertIn(test_tag, tag_list)

    def test_clone_brings_tags(self):
        cloned_tag = 'tag_from_repo_A_for_repo_B'
        self.repo.tag(cloned_tag)

        repo_c_path = self.create_tempdir()
        repo_c = git.GitRepo.clone(self.repo.repo_dir, repo_c_path)

        tag_list = repo_c.list_tags()
        self.assertIn(cloned_tag, tag_list)

    def test_duplicate_tag_updates(self):
        test_tag = 'duplicate_me'
        self.repo.tag(test_tag)
        self.repo.commit(stage=False)
        output = self.repo.tag(test_tag)
        msg = "updated tag '%s'" % test_tag
        self.assertIn(msg.lower(), output.lower())

    def test_duplicate_tag_fails_without_force(self):
        test_tag = 'duplicate_me'
        self.repo.tag(test_tag)
        self.assertRaises(
            exceptions.SimplGitCommandError, self.repo.tag,
            test_tag, force=False)

    def test_tag_with_spaces_fails(self):
        test_tag = 'x k c d'
        self.assertRaises(
            exceptions.SimplGitCommandError, self.repo.tag, test_tag)

    def test_annotated_tag(self):
        test_tag = 'v2.0.0'
        test_message = "2 is better than 1"
        self.repo.tag(test_tag, message=test_message)
        tags = self.repo.list_tags(with_messages=False)
        self.assertIn('v2.0.0', tags)
        tags = self.repo.list_tags(with_messages=True)
        self.assertIn((test_tag, test_message), tags)

    def test_commit_ammend(self):
        t = self.repo.commit(message='amend me')
        self.assertTrue(self.repo.commit(amend=True))

    def test_commit_automatically_stages(self):
        temp = tempfile.NamedTemporaryFile(
            dir=self.repo.repo_dir, suffix='.simpltest')
        temp.write("calmer than you are".encode('utf-8'))
        temp.flush()
        msg = "1 file changed"
        output = self.repo.commit(message="dudeism")
        self.assertIn(msg.lower(), output.lower())
        self.assertIn('dudeism', output.lower())

    def test_commit_with_long_message(self):
        hash_before = self.repo.head
        self.repo.commit(message='fix(api): dont implode', stage=False)
        hash_after = self.repo.head
        self.assertNotEqual(hash_before, hash_after)

    def test_checkout(self):
        hash_before = self.repo.head
        self.repo.tag('tag_before_changes')

        temp = tempfile.NamedTemporaryFile(
            dir=self.repo.repo_dir, suffix='.simpltest')
        temp.file.write("calmer than you are".encode('utf-8'))
        self.repo.commit(message="dudeism")
        hash_after = self.repo.head
        self.repo.tag('tag_after_changes')
        self.repo.checkout('tag_before_changes')
        self.assertNotEqual(hash_before, hash_after)
        self.assertEqual(self.repo.head, hash_before)
        self.repo.checkout('tag_after_changes')
        self.assertEqual(self.repo.head, hash_after)

    def test_checkout_dash_b(self):
        hash_before = self.repo.head
        self.repo.tag('tag_before_changes')
        temp = tempfile.NamedTemporaryFile(
            dir=self.repo.repo_dir, suffix='.simpltest')
        temp.file.write("calmer than you are".encode('utf-8'))
        self.repo.commit(message="dudeism")
        hash_after = self.repo.head
        self.repo.tag('tag_after_changes')
        self.repo.checkout('tag_before_changes',  branch='new')
        self.assertEqual(self.repo.current_branch, 'new')
        self.assertEqual(self.repo.head, hash_before)

    def test_fetch_checkout_remote(self):
        cloned_tag = 'tag_from_repo_A_for_repo_B'
        self.repo.tag(cloned_tag)
        # init, fetch, and checkout instead of cloning
        self.repo_b.fetch(
            remote=self.repo.repo_dir, refspec=cloned_tag, tags=True)
        self.repo_b.fetch(
            remote=self.repo.repo_dir, refspec=cloned_tag, tags=False)
        self.repo_b.checkout(cloned_tag)
        tags = self.repo_b.list_tags()
        self.assertIn(cloned_tag, tags)
        self.assertEqual(self.repo.head, self.repo_b.head)

    def test_fetch_checkout_remote_commit(self):
        new_commit_hash = self.repo.head
        self.repo_b.fetch(remote=self.repo.repo_dir, tags=True)
        self.repo_b.fetch(remote=self.repo.repo_dir, tags=False)
        self.repo_b.checkout(new_commit_hash)
        self.assertEqual(self.repo.head, self.repo_b.head)

    def test_pull_remote(self):
        self.repo.tag('tag_to_pull')
        self.repo_b.pull(remote=self.repo.repo_dir, ref='tag_to_pull')
        self.repo_b.checkout('FETCH_HEAD')
        self.assertEqual(self.repo.head, self.repo_b.head)

    def test_simplgitexception_bad_command(self):
        with self.assertRaises(OSError):
            try:
                self.repo.run_command(['git-crazy'])
            except exceptions.SimplGitCommandError as err:
                self.assertTrue(err.oserror)
                raise err.oserror


class TestGitVersion(unittest.TestCase):

    def test_check_git_version_no_git(self):
        # Check that a warning is raised if git isn't installed.
        with mock.patch.object(git, 'git_version') as gitv:
            gitv.side_effect = exceptions.SimplGitCommandError(
                127, 'git version',
                output="OSError(2, 'No such file or directory')")
            with warnings.catch_warnings(record=True) as caught:
                git.check_git_version()
                self.assertEqual(len(caught), 1)
                warning = caught[-1]
                self.assertEqual("Git does not appear to be installed!",
                                 str(warning.message))

    def test_check_git_version_old(self):
        # Check that a warning is raised if the installed git version is older
        # than recommended.
        with mock.patch.object(git, 'git_version') as gitv:
            gitv.return_value = 'git version 1.8.5.6'
            with warnings.catch_warnings(record=True) as caught:
                git.check_git_version()
                self.assertEqual(len(caught), 1)
                warning = caught[-1]
                self.assertEqual(
                    "Git version 1.8.5.6 found. 1.9 or greater "
                    "is recommended for simpl/git.py",
                    str(warning.message))


if __name__ == '__main__':
    unittest.main()
