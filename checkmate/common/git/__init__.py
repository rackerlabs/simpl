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
"""Common git commands and local repository wrapper class."""
import errno
import os
import pipes

from checkmate import utils


def git_init(repo_dir):
    """Do a git init in `repo_dir'."""
    return utils.execute_shell('git init', cwd=repo_dir)


def git_clone(target_dir, location, branch_or_tag=None, verbose=False):
    """Do a git checkout of `head' in `repo_dir'."""
    target_dir = pipes.quote(target_dir)
    command = 'git clone'
    if verbose:
        command = "%s --verbose" % command
    command = '%s %s %s' % (command, location, target_dir)
    if branch_or_tag:
        command = "%s --branch %s" % (command, branch_or_tag)
    return utils.execute_shell(command)


def git_remote_tag_exists(repo_dir, tag, remote='origin'):
    """Return True if 'tag' matches an existing remote tag name."""
    output = utils.execute_shell('git ls-remote %s %s' % (remote, tag),
                                 cwd=repo_dir)
    if output['stdout']:
        return True
    return False


def git_tag(repo_dir, tagname, message=None, force=True):
    """Create an annotated tag at the current HEAD."""
    message = pipes.quote(message or "%s" % tagname)
    command = 'git tag --annotate --message %s' % message
    if force:
        command = "%s --force" % command
    # append the tag as the final arg
    command = "%s %s" % (command, pipes.quote(tagname))
    return utils.execute_shell(command, cwd=repo_dir)


def git_list_tags(repo_dir, with_messages=False):
    """Return a list of git tags for the git repo in `repo_dir'."""
    command = 'git tag -l'
    if with_messages:
        command = "%s -n1" % command
    return utils.execute_shell(command, cwd=repo_dir)['stdout'].splitlines()


def git_checkout(repo_dir, ref):
    """Do a git checkout of `ref' in `repo_dir'."""
    return utils.execute_shell('git checkout --force %s'
                               % ref, cwd=repo_dir)


def git_fetch(repo_dir, remote="origin", refspec=None, verbose=False):
    """Do a git fetch of `refspec' in `repo_dir'."""
    command = 'git fetch --update-head-ok --tags'
    if verbose:
        command = "%s --verbose" % command
    if refspec:
        command = "%s %s %s" % (command, remote, pipes.quote(refspec))
    else:
        command = "%s %s" % (command, remote)
    return utils.execute_shell(command, cwd=repo_dir)


def git_pull(repo_dir, remote="origin", ref=None):
    """Do a git pull of `ref' from `remote'."""
    command = 'git pull --update-head-ok %s' % remote
    if ref:
        command = "%s %s" % (command, pipes.quote(ref))
    return utils.execute_shell(command, cwd=repo_dir)


def git_commit(repo_dir, message=None, amend=False, stage=True):
    """Commit any changes, optionally staging all changes beforehand."""
    if stage:
        git_add_all(repo_dir)
    command = "git commit --allow-empty"
    if amend:
        command = "%s --amend" % command
        if not message:
            command = "%s --no-edit" % command
    if message:
        command = "%s --message %s" % (command, pipes.quote(message))
    elif not amend:
        # if not amending and no message, allow an empty message
        command = "%s --message='' --allow-empty-message" % command
    return utils.execute_shell(command, cwd=repo_dir)


def git_add_all(repo_dir):
    """Stage all changes in the working tree."""
    return utils.execute_shell('git add --all', cwd=repo_dir)


def git_status(repo_dir):
    """Get the working tree status."""
    return utils.execute_shell('git status', cwd=repo_dir)


def git_head_commit(repo_dir):
    """Return the current commit hash HEAD points to."""
    return utils.execute_shell(
        'git rev-parse HEAD', cwd=repo_dir)['stdout']


class GitRepo(object):

    """Wrapper on a git repository.

    Most commands return a dict with 'returncode' and 'stdout'.
    The executor combines stderr and stdout, so any stderr will
    return under the 'stdout' key in the dictionary.

    Unless 'repo_dir' is already an initialized git repository,
    the first method you will need to run will probably be
    self.init() or self.clone()
    """

    def __init__(self, repo_dir):
        """Initialize wrapper and check for existence of dir."""
        if not os.path.exists(repo_dir):
            raise OSError(errno.ENOENT, "No such file or directory")
        self.repo_dir = repo_dir

    @property
    def head(self):
        """Return the current commit hash."""
        return git_head_commit(self.repo_dir)

    def status(self):
        """Get the working tree status."""
        return git_status(self.repo_dir)['stdout']

    def init(self):
        """Run `git init` in the repo_dir."""
        return git_init(self.repo_dir)

    def clone(self, location, branch_or_tag=None, verbose=False):
        """Do a git checkout of 'location' @ 'branch_or_tag'."""
        return git_clone(self.repo_dir, location,
                         branch_or_tag=branch_or_tag,
                         verbose=verbose)

    def tag(self, tagname, message=None, force=True):
        """Create an annotated tag."""
        return git_tag(self.repo_dir, tagname, message=message, force=force)

    def remote_tag_exists(self, tag, remote='origin'):
        """Determine if 'tag' matches an existing remote tag name."""
        return git_remote_tag_exists(self.repo_dir, tag, remote=remote)

    def list_tags(self, with_messages=False):
        """Return a list of git tags for the git repo.

        If 'with_messages' is True, returns
        a list of (tag, message) tuples
            [(<tag1>, <message1>), (<tag2>, <message2>)]
        """
        output = git_list_tags(
            self.repo_dir, with_messages=with_messages)
        output = [l for l in output if l.strip()]
        if with_messages:
            output = [tuple(j.strip() for j in line.split(' ', 1))
                      for line in output]
        return output

    def checkout(self, ref):
        """Do a git checkout of `ref'."""
        return git_checkout(self.repo_dir, ref)

    def fetch(self, remote="origin", refspec=None, verbose=False):
        """Do a git fetch of `refspec'."""
        return git_fetch(self.repo_dir, remote=remote,
                         refspec=refspec, verbose=verbose)

    def pull(self, remote="origin", ref=None):
        """Do a git pull of `ref' from `remote'."""
        return git_pull(self.repo_dir, remote=remote, ref=ref)

    def add_all(self):
        """Stage all changes in the working tree."""
        return git_add_all(self.repo_dir)

    def commit(self, message=None, amend=False, stage=True):
        """Commit any changes, optionally staging all changes beforehand."""
        return git_commit(self.repo_dir, message=message,
                          amend=amend, stage=stage)
