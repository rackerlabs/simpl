# Copyright (c) 2011-2015 Rackspace US, Inc.
#
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
"""Simpl exceptions and warnings.

Warnings can be imported and subsequently disabled by
calling the disable() classmethod.

TODO(sam): add SimpleConfigException and NoGroupForOption
"""

import warnings

__all__ = (
    'GitWarning',
    'SimplException',
    'SimplGitError',
    'SimplGitCommandError',
    'SimplGitNotRepo',
    'SimplCalledProcessError',
)


class GitWarning(RuntimeWarning):

    """The local git program is missing or may be incompatible."""

    @classmethod
    def disable(cls):
        """Disable warnings of this type."""
        return warnings.simplefilter('ignore', cls)

# shown until proven ignored :)
warnings.simplefilter('always', GitWarning)


class SimplException(Exception):

    """Base exception for all exceptions raised by the simpl package."""


class SimplGitError(SimplException):

    """Base class for errors from the git module."""


class SimplGitCommandError(SimplGitError):

    """Raised when an error occurs while trying a git command."""

    def __init__(self, returncode, cmd, output=None, oserror=None):
        """Customize Exception Constructor."""
        super(SimplGitCommandError, self).__init__()
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
        self.oserror = oserror

    def __str__(self):
        """Include custom data in string."""
        return ("The command `%s` returned non-zero exit status %d and "
                "produced the following output: \"%s\""
                % (self.cmd, self.returncode, self.output))

    def __repr__(self):
        """Include custom data in representation."""
        rpr = ('SimplGitCommandError(%d, `%s`, output="%s"'
               % (self.returncode, self.cmd, self.output))
        if self.oserror:
            rpr += ', oserror=%s' % repr(self.oserror)
        rpr += ')'
        return rpr


class SimplGitNotRepo(SimplGitError):

    """The directory supplied is not a git repo."""


class SimplCalledProcessError(SimplException):

    """Raised when a process run by execute() returns non-zero.

    The exit status will be stored in the returncode attribute;
    check_output() will also store the output in the output attribute.
    """

    def __init__(self, returncode, cmd, output=None):
        """Customize Exception Constructor."""
        super(SimplCalledProcessError, self).__init__()
        self.returncode = returncode
        self.cmd = cmd
        self.output = output

    def __str__(self):
        """Include custom data in string."""
        return ("Command '%s' returned non-zero exit status %d"
                % (self.cmd, self.returncode))
