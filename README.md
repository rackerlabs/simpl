# simpl

Common Python libraries for:

- [Configuration](#config)
- [Logging](#logging)
- [Secrets](#secrets)
- [WSGI Middleware](#middleware)

## <a name="config"></a>Config

Supports argparse-like configuration options with support for the following
configuration methods:
- command-line arguments
- environment variables
- keychain (OSX) and keyring (Linux)
- ini/config files

## <a name="logging"></a>Logging (simpl.log)

Encapsulates logging boilerplate code to initialize logging using the
[config](#config) module.

## <a name="secrets"></a>Sensitive Value Helpers

Helpers for managing sensitive values.

## <a name="middleware"></a>WSGI middleware

Includes sample middleware for use with WSGI apps including bottle.

Middleware included:
- CORS: handles CORS requests


## release
[![latest](https://img.shields.io/pypi/v/simpl.svg)](https://pypi.python.org/pypi/simpl)

## builds

| Branch        | Status  |
| ------------- | ------------- |
| [master](https://github.com/checkmate/simpl/tree/master)  | [![Build Status](https://travis-ci.org/checkmate/simpl.svg?branch=master)](https://travis-ci.org/checkmate/simpl)  |
