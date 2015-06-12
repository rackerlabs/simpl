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

"""Simpl git utilities.

Wraps many shellouts to git creating
easy-to-handle, pythonic results.

Tested against:

    git 2.1.2

"""

import atexit
import errno
import logging
import os
import pipes
import shutil
import tempfile
import warnings

from six.moves import zip_longest

from simpl import exceptions
from simpl.utils import shell

LOG = logging.getLogger(__name__)
#: Minimum recommended git version
MIN_GIT_VERSION = (1, 9)


def execute_git_command(command, repo_dir=None):
    """Execute a git command and return the output.

    Catches CalledProcessErrors and OSErrors, wrapping them
    in a more useful SimplGitCommandError.

    Raises SimplCommandGitError if the command fails. Returncode and
    output from the attempt can be found in the SimplGitCommandError
    attributes.
    """
    try:
        output = shell.execute(command, cwd=repo_dir)
    except exceptions.SimplCalledProcessError as err:
        raise exceptions.SimplGitCommandError(err.returncode, err.cmd,
                                              output=err.output)
    except OSError as err:
        # OSError's errno *is not* the returncode
        raise exceptions.SimplGitCommandError(
            127, command, output=repr(err), oserror=err)
    else:
        return output


def git_version():
    """Get the `git version`."""
    return execute_git_command(['git', '--version'])


def check_git_version():
    """Check the installed git version against a known-stable version.

    If the git version is less then ``MIN_GIT_VERSION``, a warning is raised.

    If git is not installed at all on this system, we also raise a warning for
    that.

    The original reason why this check was introduced is because with older
    versions git (< 1.9), newly init-ed git repos cannot checkout from a
    fetched remote unless the repo has at least one commit in it. The reason
    for this is that before creating a commit, the HEAD refers to a
    refs/heads/master file which doesn't exist yet.

    TODO(larsbutler): If we wanted to be defensive about this and favor
    compatibility over elegance, we could just automatically add a `git commit`
    (empty, no message) after every `git init`. I would recommend doing this in
    the :class:`GitRepo` class, not in the module-level util functions. Adding
    an extra commit shouldn't cause any problems.
    """
    try:
        version = git_version()
    except exceptions.SimplGitCommandError:
        warnings.warn("Git does not appear to be installed!",
                      exceptions.GitWarning)
        return

    ver_num = version.split()[2]
    major, minor, _ = ver_num.split('.', 2)
    major = int(major)
    minor = int(minor)
    if (major, minor) < MIN_GIT_VERSION:
        warnings.warn(
            "Git version %(ver)s found. %(rec)s or greater "
            "is recommended for simpl/git.py"
            % dict(ver=ver_num,
                   rec='.'.join((str(x) for x in MIN_GIT_VERSION))),
            exceptions.GitWarning)

# Check the git version whenever this module is used:
check_git_version()


def git_init(repo_dir):
    """Run git init in `repo_dir'."""
    return execute_git_command(['git', 'init'], repo_dir=repo_dir)


def git_clone(target_dir, repo_location, branch_or_tag=None, verbose=True):
    """Clone repo at repo_location to target_dir and checkout branch_or_tag.

    If branch_or_tag is not specified, the HEAD of the primary
    branch of the cloned repo is checked out.
    """
    target_dir = pipes.quote(target_dir)
    command = ['git', 'clone']
    if verbose:
        command.append('--verbose')
    if os.path.isdir(repo_location):
        command.append('--no-hardlinks')
    command.extend([pipes.quote(repo_location), target_dir])
    if branch_or_tag:
        command.extend(['--branch', branch_or_tag])
    return execute_git_command(command)


def git_tag(repo_dir, tagname, message=None, force=True):
    """Create an annotated tag at the current head."""
    message = message or "%s" % tagname
    command = ['git', 'tag', '--annotate', '--message', message]
    if force:
        command.append('--force')
    # append the tag as the final arg
    command.append(tagname)
    return execute_git_command(command, repo_dir=repo_dir)


def git_list_config(repo_dir):
    """Return a list of the git configuration."""
    command = ['git', 'config', '--list']
    raw = execute_git_command(command, repo_dir=repo_dir).splitlines()
    output = {key: val for key, val in
              [cfg.split('=', 1) for cfg in raw]}
    # TODO(sam): maybe turn this into more easily navigable
    # nested dicts?
    # e.g. {'alias': {'branches': ..., 'remotes': ...}}
    return output


def git_list_tags(repo_dir, with_messages=False):
    """Return a list of git tags for the git repo in `repo_dir'."""
    command = ['git', 'tag', '-l']
    if with_messages:
        command.append('-n1')
    raw = execute_git_command(command, repo_dir=repo_dir).splitlines()
    output = [l.strip() for l in raw if l.strip()]
    if with_messages:
        output = [tuple(j.strip() for j in line.split(None, 1))
                  for line in output]
    return output


def git_list_branches(repo_dir):
    """Return a list of git branches for the git repo in 'repo_dir'.

    Returns
        [
            {'branch': <branchname,
             'commit': <commit_hash>,
             'message': <commit message>},
            {...},
        ]
    """
    command = ['git', 'branch', '--remotes', '--all',
               '--verbose', '--no-abbrev']
    output = execute_git_command(command, repo_dir=repo_dir).splitlines()
    # remove nullish lines
    lines = [l.strip() for l in output if l.strip()]
    # find the * current branch
    try:
        current_branch = [l for l in lines if l.startswith('* ')][0]
    except IndexError:
        current_branch = None
    item = None
    if current_branch:
        lines.remove(current_branch)
        current_branch = current_branch.replace('* ', '', 1)
        if current_branch.startswith('(detached from '):
            branch, rest = current_branch.split(')', 1)
            branch = "%s)" % branch
            sha, msg = rest.split(None, 1)
            item = {'branch': branch, 'commit': sha, 'message': msg}
        else:
            lines.insert(0, current_branch)
    # <branch> <hash> <commit_message>
    # make a list of lists with clean elements of equal length
    breakout = [k.split(None, 2) for k in lines]
    # remove any strange hashless outliers
    breakout = [k for k in breakout if len(k[1]) == 40]
    headers = ['branch', 'commit', 'message']
    # use izip_longest so we fill in None if message was empty
    result = [dict(zip_longest(headers, vals))
              for vals in breakout]
    if item:
        result.append(item)
    return result


def git_list_remotes(repo_dir):
    """Return a listing of configured remotes."""
    command = ['git', 'remote', '--verbose', 'show']
    raw = execute_git_command(command, repo_dir=repo_dir).splitlines()
    output = [l.strip() for l in raw if l.strip()]
    # <name> <location> (<cmd>)
    # make a list of lists with clean elements of equal length
    headers = ['name', 'location', 'cmd']
    breakout = [k.split(None, len(headers)) for k in output]
    # use izip_longest so we fill in None if message was empty
    return [dict(zip_longest(headers, vals))
            for vals in breakout]


def git_list_refs(repo_dir):
    """List references available in the local repo with commit ids.

    This is similar to ls-remote, but shows the *local* refs.

    Returns
        {<ref1>: <commit_hash1>,
         <ref2>: <commit_hash2>,
         ...,
         <refN>: <commit_hashN>,
        }
    """
    command = ['git', 'show-ref', '--dereference', '--head']
    raw = execute_git_command(command, repo_dir=repo_dir).splitlines()
    output = [l.strip() for l in raw if l.strip()]
    return {ref: commit_hash for commit_hash, ref in
            [l.split(None, 1) for l in output]}


def git_ls_remote(repo_dir, remote='origin', refs=None):
    """Run git ls-remote.

    'remote' can be a remote ref in a local repo, e.g. origin,
    or url of a remote repository.

    Returns
        {<ref1>: <commit_hash1>,
         <ref2>: <commit_hash2>,
         ...,
         <refN>: <commit_hashN>,
        }
    """
    command = ['git', 'ls-remote', pipes.quote(remote)]
    if refs:
        if isinstance(refs, list):
            command.extend(refs)
        else:
            command.append(refs)
    raw = execute_git_command(command, repo_dir=repo_dir).splitlines()
    output = [l.strip() for l in raw if l.strip()
              and not l.strip().lower().startswith('from ')]
    return {ref: commit_hash for commit_hash, ref in
            [l.split(None, 1) for l in output]}


def git_branch(repo_dir, branch_name, start_point='HEAD',
               force=True, verbose=True, checkout=False):
    """Create a new branch like `git branch <branch_name> <start_point>`."""
    command = ['git', 'branch']
    if verbose:
        command.append('--verbose')
    if force:
        command.append('--force')
    command.extend([branch_name, start_point])
    branch_output = execute_git_command(command, repo_dir=repo_dir)
    if checkout:
        return git_checkout(repo_dir, branch_name)
    else:
        return branch_output


def git_checkout(repo_dir, ref, branch=None):
    """Do a git checkout of `ref' in `repo_dir'.

    If branch is specified it should be the name of the new branch.
    """
    command = ['git', 'checkout', '--force']
    if branch:
        command.extend(['-B', '{}'.format(branch)])
    command.append(ref)
    return execute_git_command(command, repo_dir=repo_dir)


def git_fetch(repo_dir, remote=None, refspec=None, verbose=False, tags=True):
    """Do a git fetch of `refspec' in `repo_dir'.

    If 'remote' is None, all remotes will be fetched.
    """
    command = ['git', 'fetch']
    if not remote:
        command.append('--all')
    else:
        remote = pipes.quote(remote)
    command.extend(['--update-head-ok'])
    if tags:
        command.append('--tags')
    if verbose:
        command.append('--verbose')
    if remote:
        command.append(remote)
    if refspec:
        command.append(refspec)
    return execute_git_command(command, repo_dir=repo_dir)


def git_pull(repo_dir, remote="origin", ref=None):
    """Do a git pull of `ref' from `remote'."""
    command = ['git', 'pull', '--update-head-ok', pipes.quote(remote)]
    if ref:
        command.append(ref)
    return execute_git_command(command, repo_dir=repo_dir)


def git_commit(repo_dir, message=None, amend=False, stage=True):
    """Commit any changes, optionally staging all changes beforehand."""
    if stage:
        git_add_all(repo_dir)
    command = ['git', 'commit', '--allow-empty']
    if amend:
        command.append('--amend')
        if not message:
            command.append('--no-edit')
    if message:
        command.extend(['--message', pipes.quote(message)])
    elif not amend:
        # if not amending and no message, allow an empty message
        command.extend(['--message=', '--allow-empty-message'])
    return execute_git_command(command, repo_dir=repo_dir)


def git_ls_tree(repo_dir, treeish='HEAD'):
    """Run git ls-tree."""
    command = ['git', 'ls-tree', '-r', '--full-tree', treeish]
    raw = execute_git_command(command, repo_dir=repo_dir).splitlines()
    output = [l.strip() for l in raw if l.strip()]
    # <mode> <type> <object> <file>
    # make a list of lists with clean elements of equal length
    breakout = [k.split(None, 3) for k in output]
    headers = ['mode', 'type', 'object', 'file']
    return [dict(zip(headers, vals)) for vals in breakout]


def git_add_all(repo_dir):
    """Stage all changes in the working tree."""
    command = ['git', 'add', '--all']
    return execute_git_command(command, repo_dir=repo_dir)


def git_status(repo_dir):
    """Get the working tree status."""
    command = ['git', 'status']
    return execute_git_command(command, repo_dir=repo_dir)


def git_head_commit(repo_dir):
    """Return the current commit hash head points to."""
    command = ['git', 'rev-parse', 'HEAD']
    return execute_git_command(command, repo_dir=repo_dir)


def git_current_branch(repo_dir):
    """Return the current branch name.

    If the repo is in 'detached HEAD' state, this just returns "HEAD".
    """
    command = ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
    return execute_git_command(command, repo_dir=repo_dir)


def is_git_repo(repo_dir):
    """Return True if the directory is inside a git repo."""
    command = ['git', 'rev-parse']
    try:
        execute_git_command(command, repo_dir=repo_dir)
    except exceptions.SimplGitCommandError:
        return False
    else:
        return True


def git_remote_resolve_reference(repo_dir, ref, remote='origin'):
    """Try to find a revision (commit hash) for the ref at 'remote' repo.

    Once you have the revision (commit hash), you can check it out. Of
    course, you may have to fetch it first.

    Note: Borrowed these ideas from Chef

        https://github.com/chef/chef/blob/master/lib/chef/provider/git.rb

    Returns None if no revision is found.
    """
    ls_refs = git_ls_remote(repo_dir, remote=remote, refs='%s*' % ref)

    if ref == 'HEAD':
        return ls_refs['HEAD']
    else:
        matching_refs = [
            'refs/tags/%s^{}' % ref,
            'refs/heads/%s^{}' % ref,
            '%s^{}' % ref,
            'refs/tags/%s' % ref,
            'refs/heads/%s' % ref,
            ref,
        ]
        for _ref in matching_refs:
            if _ref in ls_refs:
                return ls_refs[_ref]


class GitRepo(object):

    """Wrapper on a git repository.

    Git command failures raise SimplGitCommandException which includes
    attributes about the returncode, error output, etc.

    Unless 'repo_dir' is already an initialized git repository,
    you will probably want to run one of the classmethod's to
    initialize a GitRepo, either GitRepo.init() or GitRepo.clone(),
    both of which return an instance of GitRepo.

    An attempt to instantiate GitRepo with a path that is not at/in
    a git repository will raise a SimplGitNotRepo exception.
    """

    def __init__(self, repo_dir=None):
        """Initialize wrapper and check for existence of dir.

        The init() and clone() classmethods are common ways of
        initializing an instance of GitRepo.

        Defaults to current working directory if repo_dir is not supplied.

        If the repo_dir is not a git repository, SimplGitNotRepo is raised.
        """
        repo_dir = repo_dir or os.getcwd()
        repo_dir = os.path.abspath(
            os.path.expanduser(os.path.normpath(repo_dir)))
        if not os.path.isdir(repo_dir):
            raise OSError(errno.ENOENT, "No such directory")
        if not is_git_repo(repo_dir):
            raise exceptions.SimplGitNotRepo(
                "%s is not [in] a git repo." % repo_dir)
        self.repo_dir = repo_dir
        self.temp = False
        if os.path.realpath(self.repo_dir).startswith(
                os.path.realpath(tempfile.gettempdir())):
            self.temp = True

    @classmethod
    def clone(cls, repo_location, repo_dir=None,
              branch_or_tag=None, temp=False):
        """Clone repo at repo_location into repo_dir and checkout branch_or_tag.

        Defaults into current working directory if repo_dir is not supplied.

        If 'temp' is True, a temporary directory will be created for you
        and the repository will be cloned into it. The tempdir is scheduled
        for deletion (when the process exits) through an exit function
        registered with the atexit module. If 'temp' is True, repo_dir
        is ignored.

        If branch_or_tag is not specified, the HEAD of the primary
        branch of the cloned repo is checked out.
        """
        if temp:
            reponame = repo_location.rsplit('/', 1)[-1]
            suffix = '%s.temp_simpl_GitRepo' % '_'.join(
                [str(x) for x in (reponame, branch_or_tag) if x])
            repo_dir = create_tempdir(suffix=suffix, delete=True)
        else:
            repo_dir = repo_dir or os.getcwd()
        git_clone(repo_dir, repo_location, branch_or_tag=branch_or_tag)
        # assuming no errors
        return cls(repo_dir)

    @classmethod
    def init(cls, repo_dir=None, temp=False, initial_commit=False):
        """Run `git init` in the repo_dir.

        Defaults to current working directory if repo_dir is not supplied.

        If 'temp' is True, a temporary directory will be created for you
        and the repository will be initialized. The tempdir is scheduled
        for deletion (when the process exits) through an exit function
        registered with the atexit module. If 'temp' is True, repo_dir is
        ignored.
        """
        if temp:
            suffix = '.temp_simpl_GitRepo'
            repo_dir = create_tempdir(suffix=suffix, delete=True)
        else:
            repo_dir = repo_dir or os.getcwd()
        git_init(repo_dir)
        instance = cls(repo_dir)

        # NOTE(larsbutler): If we wanted to be defensive about this and favor
        # compatibility over elegance, we could just automatically add a
        # `git commit` (empty, no message) after every `git init`. I would
        # recommend doing this in the :class:`GitRepo` class, not in the
        # module-level util functions. Adding an extra commit shouldn't cause
        # any problems.
        if initial_commit:
            # unknown revision, needs a commit to run most commands
            instance.commit(
                message='Initial commit', amend=False, stage=False)
        return instance

    @property
    def origin(self):
        """Show where the 'origin' remote ref points.

        Returns None if the 'origin' remote ref does not exist.

        If 'origin' has different locations for different commands,
        the result is ambiguous and None is returned.

        Notes:
            A repo does not necessarily have any remotes configured.
            A repo with remotes configured does not necessarily have
            an 'origin' remote ref.

            This property is for common convenience.
        """
        remotes = self.list_remotes()
        candidates = set()
        for remote_ref in remotes:
            if remote_ref['name'] == 'origin':
                candidates.add(remote_ref['location'])
        if len(candidates) == 1:
            return candidates.pop()

    @property
    def head(self):
        """Return the current commit hash."""
        return git_head_commit(self.repo_dir)

    @property
    def current_branch(self):
        """Return the current branch name.

        If the repo is in 'detached HEAD' state, this just returns "HEAD".
        """
        return git_current_branch(self.repo_dir)

    def __repr__(self):
        """Customize representation."""
        rpr = '<Simpl GitRepo'
        if self.temp:
            rpr += ' (tmp)'
        return ('%s %s at %s>'
                % (rpr, self.repo_dir,
                   hex(id(self))))

    def run_command(self, command):
        """Execute a command inside the repo."""
        return execute_git_command(command, repo_dir=self.repo_dir)

    def status(self):
        """Get the working tree status."""
        return git_status(self.repo_dir)

    def tag(self, tagname, message=None, force=True):
        """Create an annotated tag."""
        return git_tag(self.repo_dir, tagname, message=message, force=force)

    def ls(self):
        """Return a list of *all* files & dirs in the repo.

        Think of this as a recursive `ls` command from the root of the repo.
        """
        tree = self.ls_tree()
        return [t.get('file') for t in tree if t.get('file')]

    def list_remotes(self):
        """List configured remotes."""
        return git_list_remotes(self.repo_dir)

    def ls_tree(self, treeish='HEAD'):
        """List *all* files/dirs in the repo at ref 'treeish'.

        Returns
            [
                {'mode': <file permissions>,
                 'type': <git object type>, # blob, tree, commit or tag
                 'object': <object hash>,
                 'file': <path/to/file.py>},
                {...},
            ]
        """
        return git_ls_tree(self.repo_dir, treeish=treeish)

    def list_refs(self):
        """List references available in the local repo with commit ids.

        This is similar to ls-remote, but shows the *local* refs.

        Returns
            {'HEAD': <commit_hash0>,
             <ref1>: <commit_hash1>,
             <ref2>: <commit_hash2>,
             ...,
             <refN>: <commit_hashN>,
            }
        """
        return git_list_refs(self.repo_dir)

    def ls_remote(self, remote='origin', refs=None):
        """Return a mapping of refs to commit ids for the given remote.

        'remote' can be a remote ref in a local repo, e.g. origin,
        or url of a remote repository.

        Returns
            {<ref1>: <commit_hash1>,
             <ref2>: <commit_hash2>,
             ...,
             <refN>: <commit_hashN>,
            }

        If 'refs' is supplied, only matching refs are returned.
        """
        return git_ls_remote(
            self.repo_dir, remote=remote, refs=refs)

    def list_tags(self, with_messages=False):
        """Return a list of git tags for the repository.

        If 'with_messages' is True, returns
        a list of (tag, message) tuples
            [(<tag1>, <message1>), (<tag2>, <message2>)]
        """
        return git_list_tags(
            self.repo_dir, with_messages=with_messages)

    def list_config(self):
        """Return a dictionary of the git config."""
        return git_list_config(self.repo_dir)

    def list_branches(self):
        """Return a list of dicts, describing the branches.

        Returns
            [
                {'branch': <branchname,
                 'commit': <commit_hash>,
                 'message': <commit message>},
                {...},
            ]
        """
        return git_list_branches(self.repo_dir)

    def branch(self, branch_name, start_point='HEAD', force=True,
               checkout=False):
        """Create branch as in `git branch <branch_name> <start_point>`.

        If 'checkout' is True, checkout the branch after creation.
        """
        return git_branch(
            self.repo_dir, branch_name, start_point, force=force,
            checkout=checkout)

    def checkout(self, ref, branch=None):
        """Do a git checkout of `ref'."""
        return git_checkout(self.repo_dir, ref, branch=branch)

    def fetch(self, remote=None, refspec=None, verbose=False, tags=True):
        """Do a git fetch of `refspec'."""
        return git_fetch(self.repo_dir, remote=remote,
                         refspec=refspec, verbose=verbose, tags=tags)

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

    def remote_resolve_reference(self, ref, remote='origin'):
        """Resolve a reference to a remote revision."""
        return git_remote_resolve_reference(self.repo_dir, ref, remote=remote)


def _cleanup_tempdir(tempdir):
    """Clean up temp directory ignoring ENOENT errors."""
    try:
        shutil.rmtree(tempdir)
    except OSError as err:
        if err.errno != errno.ENOENT:
            raise


def create_tempdir(suffix='', prefix='tmp', directory=None, delete=True):
    """Create a tempdir and return the path.

    This function registers the new temporary directory
    for deletion with the atexit module.
    """
    tempd = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=directory)
    if delete:
        atexit.register(_cleanup_tempdir, tempd)
    return tempd
