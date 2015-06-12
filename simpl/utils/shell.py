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
"""Shell (subprocess) utilities."""

import logging
import pipes
import shlex
import subprocess

import six

from simpl import exceptions

LOG = logging.getLogger(__name__)


def execute(command, cwd=None, strip=True):
    """Execute a shell command (containing no shell operators) locally.

    If 'command' is a string, it will be split into args to be passed
    to Popen. If 'command' is a list, it will be passed to Popen as is.

    Returns the output from the command.

    Raises SimplCalledProcessError on any non-zero exit status unless
    an OSError (a common error when attempting Popen calls) is raised.

    :param command:         shell command to be executed. if the value is
                            a string, it will be split using shlex.split()
                            to return a shell-like syntax as a list. if the
                            value is a list, it will be passed directly to
                            popen.
    :param cwd:             The working directory will be changed
                            to `cwd` before the command is executed. Note
                            that this directory is not considered when
                            searching the executable, so you can't specify
                            the program's path relative to this argument.
                            Value should not be quoted or shell escaped,
                            since it is passed directly to os.chdir() by
                            subprocess.Popen
    :param strip:           Strip the output of whitespace using str.strip()
    :returns:               The output of the command (stdout + stderr) if
                            the returncode is zero, otherwise raises
                            SimplCalledProcessError

    Notes:
    In this function, Popen is called with stderr=subprocess.STDOUT, which
    sends all stderr to stdout.
    """
    if isinstance(command, six.string_types):
        cmd = shlex.split(command)
        LOG.debug("Command after split: %s", cmd)
    elif isinstance(command, list):
        cmd = command
        command = " ".join(cmd)
    else:
        raise TypeError("'command' should be a string or a list")
    LOG.debug("Executing `%s` on local machine", command)
    if cwd:
        cwd = pipes.quote(cwd)
    pope = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd,
        universal_newlines=True)
    out, err = pope.communicate()
    assert not err
    out = out.strip() if strip else out
    if pope.returncode != 0:
        raise exceptions.SimplCalledProcessError(
            pope.returncode, command, output=out)
    return out
