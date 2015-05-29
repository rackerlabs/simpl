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
"""CLI and argparse utilities."""

import argparse
import os
import sys


class HelpfulParser(argparse.ArgumentParser):
    def error(self, message, print_help=False):
        if 'too few arguments' in message:
            sys.argv.insert(0, os.path.basename(sys.argv.pop(0)))
            message = ("%s. Try getting help with `%s -h`"
                       % (message, " ".join(sys.argv)))
        if print_help:
            self.print_help()
        sys.stderr.write('\nerror: %s\n' % message)
        sys.exit(2)
