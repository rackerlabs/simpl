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
# pylint: disable=W0212

r"""Configuration Parser.

Configurable parser that will parse config files, environment variables,
keyring, and command-line arguments.



Example test.ini file:

    [defaults]
    gini=10

    [app]
    xini = 50

Example test.arg file:

    --xfarg=30

Example test.py file:

    import os
    import sys

    import config


    def main(argv):
        '''Test.'''
        options = [
            config.Option("xpos",
                          help="positional argument",
                          nargs='?',
                          default="all",
                          env="APP_XPOS"),
            config.Option("--xarg",
                          help="optional argument",
                          default=1,
                          type=int,
                          env="APP_XARG"),
            config.Option("--xenv",
                          help="environment argument",
                          default=1,
                          type=int,
                          env="APP_XENV"),
            config.Option("--xfarg",
                          help="@file argument",
                          default=1,
                          type=int,
                          env="APP_XFARG"),
            config.Option("--xini",
                          help="ini argument",
                          default=1,
                          type=int,
                          ini_section="app",
                          env="APP_XINI"),
            config.Option("--gini",
                          help="global ini argument",
                          default=1,
                          type=int,
                          env="APP_GINI"),
            config.Option("--karg",
                          help="secret keyring arg",
                          default=-1,
                          type=int),
        ]
        ini_file_paths = [
            '/etc/default/app.ini',
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'test.ini')
        ]

        # default usage
        conf = config.Config(prog='app', options=options,
                             ini_paths=ini_file_paths)
        conf.parse()
        print conf

        # advanced usage
        cli_args = conf.parse_cli(argv=argv)
        env = conf.parse_env()
        secrets = conf.parse_keyring(namespace="app")
        ini = conf.parse_ini(ini_file_paths)
        sources = {}
        if ini:
            for key, value in ini.iteritems():
                conf[key] = value
                sources[key] = "ini-file"
        if secrets:
            for key, value in secrets.iteritems():
                conf[key] = value
                sources[key] = "keyring"
        if env:
            for key, value in env.iteritems():
                conf[key] = value
                sources[key] = "environment"
        if cli_args:
            for key, value in cli_args.iteritems():
                conf[key] = value
                sources[key] = "command-line"
        print '\n'.join(['%s:\t%s' % (k, v) for k, v in sources.items()])


    if __name__ == "__main__":
        if config.keyring:
            config.keyring.set_password("app", "karg", "13")
        main(sys.argv)

Example results:

    $APP_XENV=10 python test.py api --xarg=2 @test.arg
    <Config xpos=api, gini=1, xenv=10, xini=50, karg=13, xarg=2, xfarg=30>
    xpos:   command-line
    xenv:   environment
    xini:   ini-file
    karg:   keyring
    xarg:   command-line
    xfarg:  command-line

Another common pattern is to support supplying a key as a file or string value.
That can be accomplished with mutually exclusive keys (a standard feature of
argparser), the `dest` parameter (also a standard argparse feature), and the
`read_from` type.

    contrib.config.Option(
        '--my-pkey',
        mutually_exclusive_group='my_key',
        env='MY_PKEY'),
    contrib.config.Option(
        '--my-pkey-file',
        type=contrib.config.read_from,  # get the file contents (or err out)
        dest='my_pkey',  # write to the same dest as the string option
        mutually_exclusive_group='my_key',  # only one options should be set
        env='MY_PKEY_FILE')
"""

import argparse
import collections
import ConfigParser
import copy
import logging
import os
import sys

try:
    import keyring
except ImportError:
    keyring = None  # pylint: disable=C0103

LOG = logging.getLogger(__name__)


class Option(object):

    """Holds a configuration option and the names and locations for it.

    Instantiate options using the same arguments as you would for an
    add_arguments call in argparse. However, you have two additional kwargs
    available:

        env: the name of the environment variable to use for this option
        ini_section: the ini file section to look this value up from
        mutually_exclusive_group: the name of the mutually exclusive group
                                  this option will be a part of.
    """

    def __init__(self, *args, **kwargs):
        """Initialize options."""
        self.args = args or []
        self.kwargs = kwargs or {}
        self._megroup = None
        self._action = None

    def add_argument(self, parser, permissive=False, **override_kwargs):
        """Add an option to a an argparse parser.

        :keyword permissive: when true, build a parser that does not validate
            required arguments.
        """
        kwargs = {}
        if self.kwargs:
            kwargs = copy.copy(self.kwargs)
            if 'env' in kwargs and 'help' in kwargs:
                kwargs['help'] = "%s (or set %s)" % (kwargs['help'],
                                                     kwargs['env'])
            if permissive:
                try:
                    del kwargs['required']
                except KeyError:
                    pass
            try:
                del kwargs['env']
            except KeyError:
                pass
            try:
                del kwargs['ini_section']
            except KeyError:
                pass
            if 'mutually_exclusive_group' in kwargs:
                required = kwargs.pop('required', None)
                groupname = kwargs.pop('mutually_exclusive_group')
                megroup = [grp for grp in parser._mutually_exclusive_groups
                           if grp.title == groupname]
                if megroup:
                    if len(megroup) != 1:
                        raise ValueError(
                            "Bug: Mutiple mutually exclusive "
                            "groups with the same title were found.")
                    megroup = megroup[0]
                    action = megroup.add_argument(*self.args, **kwargs)
                else:
                    megroup = parser.add_mutually_exclusive_group(
                        required=required)
                    megroup.title = groupname
                    action = megroup.add_argument(*self.args, **kwargs)
                self._megroup = megroup
                self._action = action

                return
        kwargs.update(override_kwargs)
        parser.add_argument(*self.args, **kwargs)

    @property
    def type(self):
        """The type of the option.

        Should be a callable to parse options.
        """
        return self.kwargs.get("type", str)

    @property
    def name(self):
        """The name of the option as determined from the args."""
        for arg in self.args:
            if arg.startswith("--"):
                return arg[2:].replace("-", "_")
            elif arg.startswith("-"):
                continue
            else:
                return arg.replace("-", "_")

    @property
    def dest(self):
        """The destination name of the option as determined from the args."""
        if 'dest' in self.kwargs:
            return self.kwargs['dest']
        return self.name

    @property
    def default(self):
        """The default for the option."""
        return self.kwargs.get("default")


class Config(collections.MutableMapping):

    """Parses configuration sources."""

    def __init__(self, options=None, ini_paths=None, **parser_kwargs):
        """Initialize with list of options.

        :param ini_paths: optional paths to ini files to look up values from
        :param parser_kwargs: kwargs used to init argparse parsers.
        """
        self._parser_kwargs = parser_kwargs or {}
        self._ini_paths = ini_paths or []
        self._options = copy.copy(options) or []
        self._values = {option.name: option.default
                        for option in self._options}
        self._parser = argparse.ArgumentParser(**parser_kwargs)
        self.pass_thru_args = []

    @classmethod
    def init(cls, *args, **kwargs):
        """Initialize the config like as you would a regular dict."""
        instance = cls()
        instance._values.update(dict(*args, **kwargs))
        return instance

    @property
    def prog(self):
        """Program name."""
        return self._parser.prog

    def __getitem__(self, key):
        """Get item from config."""
        return self._values[key]

    def __setitem__(self, key, value):
        """Set item in config."""
        self._values[key] = value

    def __delitem__(self, key):
        """Delete item from config."""
        del self._values[key]

    def __iter__(self):
        """Iterate config."""
        return iter(self._values)

    def __len__(self):
        """Check number of config options."""
        return len(self._values)

    def __getattr__(self, attr):
        """Get attribute."""
        if attr in self._values:
            return self._values[attr]
        else:
            raise AttributeError("'config' object has no attribute '%s'"
                                 % attr)

    def build_parser(self, options, permissive=False, **override_kwargs):
        """Construct an argparser from supplied options.

        :keyword override_kwargs: keyword arguments to override when calling
            parser constructor.
        :keyword permissive: when true, build a parser that does not validate
            required arguments.
        """
        kwargs = copy.copy(self._parser_kwargs)
        kwargs.setdefault('formatter_class',
                          argparse.ArgumentDefaultsHelpFormatter)
        kwargs.update(override_kwargs)
        if 'fromfile_prefix_chars' not in kwargs:
            kwargs['fromfile_prefix_chars'] = '@'
        parser = argparse.ArgumentParser(**kwargs)
        if options:
            for option in options:
                option.add_argument(parser, permissive=permissive)
        return parser

    def parse_cli(self, argv=None, permissive=False):
        """Parse command-line arguments into values.

        :keyword permissive: when true, does not validate required or extra
            arguments.
        """
        if argv is None:
            argv = sys.argv
        options = []
        for option in self._options:
            kwargs = option.kwargs.copy()
            kwargs['default'] = argparse.SUPPRESS
            temp = Option(*option.args, **kwargs)
            options.append(temp)
        parser = self.build_parser(options, permissive=permissive)
        parsed, extras = parser.parse_known_args(argv[1:])
        if extras:
            valid, pass_thru = self.parse_passthru_args(argv[1:])
            parsed, extras = parser.parse_known_args(valid)
            if extras and not permissive:
                raise AttributeError("Unrecognized arguments: %s" %
                                     ' ,'.join(extras))
            self.pass_thru_args = pass_thru + extras
        else:
            # maybe reset pass_thru_args on subsequent calls
            # parse() -> parse_cli() is called post-plugin-init
            self.pass_thru_args = []
        return vars(parsed)

    def parse_env(self, env=None, namespace=None):
        """Parse environment variables."""
        env = env or os.environ
        results = {}
        if not namespace:
            namespace = self.prog
        namespace = namespace.upper()
        for option in self._options:
            env_var = option.kwargs.get('env')
            default_env = "%s_%s" % (namespace, option.name.upper())
            if env_var and env_var in env:
                value = env[env_var]
                results[option.dest] = option.type(value)
            elif default_env in env:
                value = env[default_env]
                results[option.dest] = option.type(value)

        return results

    def get_defaults(self):
        """Use argparse to determine and return dict of defaults."""
        parser = self.build_parser(self._options, permissive=True)
        parsed, _ = parser.parse_known_args([])
        return vars(parsed)

    def parse_ini(self, paths=None):
        """Parse config files and return configuration options.

        Expects array of files that are in ini format.
        :param paths: list of paths to files to parse (uses ConfigParse logic).
                      If not supplied, uses the ini_paths value supplied on
                      initialization.
        """
        results = {}
        config = ConfigParser.SafeConfigParser()
        config.read(paths or self._ini_paths)
        for option in self._options:
            ini_section = option.kwargs.get('ini_section')
            if ini_section:
                try:
                    value = config.get(ini_section, option.name)
                    results[option.dest] = option.type(value)
                except ConfigParser.NoSectionError:
                    pass
        return results

    def parse_keyring(self, namespace=None):
        """Find settings from keyring."""
        results = {}
        if not keyring:
            return results
        if not namespace:
            namespace = self.prog
        for option in self._options:
            secret = keyring.get_password(namespace, option.name)
            if secret:
                results[option.dest] = option.type(secret)
        return results

    def load_options(self, argv=None, keyring_namespace=None):
        """Find settings from all sources."""
        defaults = self.get_defaults()
        args = self.parse_cli(argv=argv, permissive=True)
        env = self.parse_env()
        secrets = self.parse_keyring(keyring_namespace)
        ini = self.parse_ini()

        results = defaults
        results.update(ini)
        results.update(secrets)
        results.update(env)
        results.update(args)
        return results

    def parse(self, argv=None, keyring_namespace=None):
        """Find settings from all sources."""
        results = self.load_options(argv=argv,
                                    keyring_namespace=keyring_namespace)
        # Run validation
        raise_for_group = {}
        for option in self._options:
            if option.kwargs.get('required'):
                if option.dest not in results or results[option.dest] is None:
                    if getattr(option, '_megroup', None):
                        raise_for_group.setdefault(option._megroup, [])
                        raise_for_group[option._megroup].append(option._action)
                    else:
                        raise SystemExit("'%s' is required. See --help "
                                         "for more info." % option.name)
                else:
                    if getattr(option, '_megroup', None):
                        raise_for_group.pop(option._megroup, None)
        if raise_for_group:
            optstrings = [str(k.option_strings)
                          for k in raise_for_group.values()[0]]
            msg = "One of %s required. " % " ,".join(optstrings)
            raise SystemExit(msg + "See --help for more info.")
        self._values = results
        return self

    @staticmethod
    def parse_passthru_args(argv):
        """Handle arguments to be passed thru to a subprocess using '--'.

        :returns: tuple of two lists; args and pass-thru-args
        """
        if '--' in argv:
            dashdash = argv.index("--")
            return argv[:dashdash], argv[dashdash + 1:]
        return argv, []

    def __repr__(self):
        """Display configured values when representing instance."""
        return "<Config %s>" % ', '.join([
            '%s=%s' % (k, v) for k, v in self.items()])


def read_from(value):
    """Read file and return contents."""
    path = normalized_path(value)
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError("%s is not a valid path." % path)
    LOG.debug("%s exists.", path)
    with open(path, 'r') as reader:
        read = reader.read()
    return read


def normalized_path(value):
    """Normalize and expand a shorthand or relative path."""
    if not value:
        return
    norm = os.path.normpath(value)
    norm = os.path.abspath(os.path.expanduser(norm))
    return norm


def comma_separated_strings(value):
    """Handle comma-separated arguments passed in command-line."""
    return [str(v) for v in value.split(",")]


def comma_separated_pairs(value):
    """Handle comma-separated key/values passed in command-line."""
    pairs = value.split(",")
    results = {}
    for pair in pairs:
        key, pair_value = pair.split('=')
        results[key] = pair_value
    return results


def parse_key_format(value):
    """Handle string formats of key files."""
    return value.strip("'").replace('\\n', '\n')
