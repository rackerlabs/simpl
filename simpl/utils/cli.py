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
"""CLI utilities."""

import argparse
import os
import sys


SimplHelpFormatter = type('SimplHelpFormatter',
                          (argparse.ArgumentDefaultsHelpFormatter,
                           argparse.RawTextHelpFormatter), {})


class HelpfulParser(argparse.ArgumentParser):

    """An argparser that won't leave you hanging."""

    def __init__(self, *args, **kwargs):
        """Set formatter_class if it is not explicitly specified."""
        kwargs.setdefault('formatter_class', SimplHelpFormatter)
        super(HelpfulParser, self).__init__(*args, **kwargs)

    def error(self, message, print_help=False):
        """Provide a more helpful message if there are too few arguments."""
        if 'too few arguments' in message.lower():
            target = sys.argv.pop(0)
            sys.argv.insert(
                0, os.path.basename(target) or os.path.relpath(target))
            message = ("%s. Try getting help with `%s --help`"
                       % (message, " ".join(sys.argv)))
        if print_help:
            self.print_help()
        else:
            self.print_usage()
        sys.stderr.write('\nerror: %s\n' % message)
        sys.exit(2)


def kwarg(string, separator='='):
    """Return a dict from a delimited string."""
    if separator not in string:
        raise ValueError("Separator '%s' not in value '%s'"
                         % (separator, string))
    if string.strip().startswith(separator):
        raise ValueError("Value '%s' starts with separator '%s'"
                         % (string, separator))
    if string.strip().endswith(separator):
        raise ValueError("Value '%s' ends with separator '%s'"
                         % (string, separator))
    if string.count(separator) != 1:
        raise ValueError("Value '%s' should only have one '%s' separator"
                         % (string, separator))
    key, value = string.split(separator)
    return {key: value}
