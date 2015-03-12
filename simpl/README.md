## config.py
##### _Configuration Parser_

Configurable parser that will parse config files, environment variables,
keyring, and command-line arguments.

##### Example `test.ini` file:

```
[defaults]
gini=10
[app]
xini = 50
```

##### Example `test.arg` file:
```
--xfarg=30
```
##### Example `test.py` file:

```python
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
```

##### Example results:
```
$APP_XENV=10 python test.py api --xarg=2 @test.arg
<Config xpos=api, gini=1, xenv=10, xini=50, karg=13, xarg=2, xfarg=30>
xpos:   command-line
xenv:   environment
xini:   ini-file
karg:   keyring
xarg:   command-line
xfarg:  command-line
```

Another common pattern is to support supplying a key as a file or string value.
That can be accomplished with mutually exclusive keys (a standard feature of
argparser), the `dest` parameter (also a standard argparse feature), and the
`read_from` type.

```python
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
```
