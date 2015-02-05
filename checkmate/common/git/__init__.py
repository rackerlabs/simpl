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


def git_tags(repo_dir):
    """Return a list of git tags for the git repo in `repo_dir'."""
    return utils.execute_shell(
        'git tag -l', cwd=repo_dir)['stdout'].splitlines()


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
        command = "%s %s %s" % (command, remote, refspec)
    else:
        command = "%s %s" % (command, remote)
    return utils.execute_shell(command, cwd=repo_dir)


def git_pull(repo_dir, remote="origin", ref=None):
    """Do a git pull of `ref' from `remote'."""
    command = 'git pull --update-head-ok %s' % remote
    if ref:
        command = "%s %s" % (command, ref)
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
        command = "%s --message %s" % (command, message)
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
