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
#
"""Logging Boilerplate.

Named `log` so as not to conflict with stdlib logging.

Implements:
- integration with :mod:`config` for configuring logging.
- enhanced handling of extra data and output formatting.


Usage with config:

- initialization

    from simpl import config
    from simpl import log

    # Add log.OPTIONS to your options when implementing config


Usage in module:

    from simpl import log  # instead of `import logging`

    LOG = log.getLogger(__name__)


"""
import logging
import os
import sys

from simpl import config

OPTIONS = [
    #
    # Verbosity, debugging, and monitoring
    #
    config.Option("--logconfig",
                  help="Optional logging configuration file"),
    config.Option("-d", "--debug",
                  default=False,
                  action="store_true",
                  help="turn on additional debugging inspection and "
                  "output including full HTTP requests and responses. "
                  "Log output includes source file path and line "
                  "numbers"),
    config.Option("-v", "--verbose",
                  default=False,
                  action="store_true",
                  help="turn up logging to DEBUG (default is INFO)"),
    config.Option("-q", "--quiet",
                  default=False,
                  action="store_true",
                  help="turn down logging to WARN (default is INFO)"),
]

getLogger = logging.getLogger  # pylint: disable=C0103


def log_level(conf):
    """Get debug settings from arguments.

    --debug: turn on additional debug code/inspection (implies
             logging.DEBUG)
    --verbose: turn up logging output (logging.DEBUG)
    --quiet: turn down logging output (logging.WARNING)
    default is logging.INFO
    """
    if conf.debug is True:
        return logging.DEBUG
    elif conf.verbose is True:
        return logging.DEBUG
    elif conf.quiet is True:
        return logging.WARNING
    else:
        return logging.INFO


def configure(conf, default_config=None):
    """Configure logging based on log config file.

    Turn on console logging if no logging files found

    :param config: object with configuration namespace (argparse parser)
    """
    if conf.logconfig and os.path.isfile(conf.logconfig):
        logging.config.fileConfig(conf.logconfig,
                                  disable_existing_loggers=False)
    elif default_config and os.path.isfile(default_config):
        logging.config.fileConfig(default_config,
                                  disable_existing_loggers=False)
    else:
        init_console_logging(conf)


def _get_debug_formatter(conf):
    """Get debug formatter based on configuration.

    :param config: configurtration namespace (ex. argparser)

    --debug: log line numbers and file data also
    --verbose: standard debug
    --quiet: turn down logging output (logging.WARNING)
    default is logging.INFO
    """
    if conf.debug is True:
        return DebugFormatter('%(pathname)s:%(lineno)d: %(levelname)-8s '
                              '%(message)s')
    elif conf.verbose is True:
        return logging.Formatter(
            '%(name)-30s: %(levelname)-8s %(message)s')
    elif conf.quiet is True:
        return logging.Formatter('%(message)s')
    else:
        return logging.Formatter(logging.BASIC_FORMAT)


def init_console_logging(conf):
    """Log to console."""
    # define a Handler which writes messages to the sys.stderr
    console = find_console_handler(logging.getLogger())
    if not console:
        console = logging.StreamHandler()
    logging_level = log_level(conf)
    console.setLevel(logging_level)

    # set a format which is simpler for console use
    formatter = _get_debug_formatter(conf)
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger().addHandler(console)
    logging.getLogger().setLevel(logging_level)
    global LOG  # pylint: disable=W0603
    LOG = logging.getLogger(__name__)  # reset


class DebugFormatter(logging.Formatter):

    """Log formatter.

    Outputs any 'data' values passed in the 'extra' parameter if provided.
    """

    def format(self, record):
        """Print out any 'extra' data provided in logs."""
        if hasattr(record, 'data'):
            return "%s. DEBUG DATA=%s" % (
                logging.Formatter.format(self, record),
                record.__dict__['data'])
        return logging.Formatter.format(self, record)


def find_console_handler(logger):
    """Return a stream handler, if it exists."""
    for handler in logger.handlers:
        if (isinstance(handler, logging.StreamHandler) and
                handler.stream == sys.stderr):
            return handler
