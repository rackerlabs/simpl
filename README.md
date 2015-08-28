# simpl
[![Build Status](https://travis-ci.org/checkmate/simpl.svg?branch=master)](https://travis-ci.org/checkmate/simpl)
[![Coverage Status](https://coveralls.io/repos/checkmate/simpl/badge.svg?branch=master)](https://coveralls.io/r/checkmate/simpl?branch=master)

Common Python libraries for:

- [Configuration](#config)
- [Logging](#logging)
- [Secrets](#secrets)
- [Python Utilites](#python)
- [WSGI Middleware](#middleware)
- [REST API Tooling](#rest)
- [Date/Time (chronos)](#chronos)
- [MongoDB Backend Wrapper](#mongo)

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


## <a name="python"></a>Python Utilities

Code we wished was built in to python (or was simpler to use):
- dictionary and list merging
- dictionary get/set/in by path

## <a name="middleware"></a>WSGI middleware

Includes sample middleware for use with WSGI apps including bottle.

Middleware included:
- CORS: handles CORS requests
- Context: handles setting a threadlocal context and adds a transaction ID.


## <a name="rest"></a>REST API Tooling

Helper code for handling RESTful APIs using bottle.

Code included:
- body: a decorator that parses a call body and passes it to a route as an argument. The decorator can apply a schema (any callable including a voluptuous.Schema), return a default, and enforce that a body is required.
- paginated: a decorator that returns paginated data with correct limit/offset validation and HTTP responses.
- process_params: parses query parameters from bottle request

## <a name="chronos"></a>Date/Time Utilites

Provides functions that consistently format date/time and timestamp data for use in APIs.

## <a name="mongo"></a>MongoDB Backend Wrapper

Implements an opinionated wrapper for MongoDB databases and collections
that works with the [rest][#rest] module and supports query param filtering
(including text search) and pagination of backend collections.

## release
[![latest](https://img.shields.io/pypi/v/simpl.svg)](https://pypi.python.org/pypi/simpl)

## builds

| Branch        | Status  |
| ------------- | ------------- |
| [master](https://github.com/checkmate/simpl/tree/master)  | [![Build Status](https://travis-ci.org/checkmate/simpl.svg?branch=master)](https://travis-ci.org/checkmate/simpl)  |
