# Copyright 2013-2015 Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Simpl's base module for its command line interface."""

import functools
import logging

from simpl import server
from simpl.utils import cli as cli_utils


PARSER = cli_utils.HelpfulParser(
    prog='simpl',
    description='Build somthing awesome.',
)
SUBPARSER = PARSER.add_subparsers(
    title='commands',
    description='Available commands',
)


def default_parser():
    """Return global argumentparser."""
    return PARSER


def default_subparser():
    """Return global argumentparser's subparser."""
    return SUBPARSER


def main(argv=None):
    """Entry point for the `simpl` command."""
    #
    # `simpl server`
    #
    logging.basicConfig(level=logging.INFO)
    server_func = functools.partial(server.main, argv=argv)
    server_parser = server.attach_parser(default_subparser())
    server_parser.set_defaults(_func=server_func)

    # the following code shouldn't need to change when
    # we add a new subcommand.
    args = default_parser().parse_args(argv)
    args._func()


if __name__ == '__main__':

    main()
