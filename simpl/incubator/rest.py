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

"""Incubator utilities for :mod:`simpl.rest`."""

import traceback

import bottle
import six  # pylint: disable=wrong-import-order
import voluptuous as volup  # pylint: disable=wrong-import-order

from simpl import rest as simpl_rest


class MultiValidationError(Exception):

    """Basically a re-imagining of a `voluptuous.MultipleInvalid` error.

    Reformats multiple errors messages for easy debugging of invalid
    Checkmatefiles.
    """

    def __init__(self, errors):
        """MultiValidationError constructor.

        :param errors:
            List of `voluptuous.Invalid` or `voluptuous.MultipleInvalid`
            exception objects.
        """
        self.errors = errors
        self.message = self._generate_message()

    def __str__(self):
        """Just return the pre-computed message.

        See :meth:`_generate_message`.
        """
        return self.message

    def __repr__(self):
        """Simple representation of the exception, with the full message."""
        indented_message = '\n'.join(
            sorted('\t' + x for x in self.message.split('\n'))
        )
        return (
            '%(cls_name)s(\n%(message)s\n)'
            % dict(cls_name=self.__class__.__name__, message=indented_message)
        )

    def _generate_message(self):
        """Reformat `path` attributes of each `error` and create a new message.

        Join `path` attributes together in a more readable way, to enable easy
        debugging of an invalid Checkmatefile.

        :returns:
            Reformatted error paths and messages, as a multi-line string.
        """
        reformatted_paths = (
            ''.join(
                "[%s]" % str(x)
                # If it's not a string, don't put quotes around it. We do this,
                # for example, when the value is an int, in the case of a list
                # index.
                if isinstance(x, six.integer_types)
                # Otherwise, assume the path node is a string and put quotes
                # around the key name, as if we were drilling down into a
                # nested dict.
                else "['%s']" % str(x)
                for x in error.path
            )
            for error in self.errors
        )

        messages = (error.msg for error in self.errors)
        # combine each path with its message:
        zipped = zip(reformatted_paths, messages)
        combined_messages = (
            '%(path)s: %(messages)s' % dict(path=path, messages=message)
            for path, message in zipped
        )

        return '\n'.join(sorted(combined_messages))


def coerce_one(schema=str):
    """Expect the input sequence to contain a single value.

    :keyword schema:
        Custom schema to apply to the input value. Defaults to just string,
        since this is designed for query params.
    """
    def validate(val):
        """Unpack a single item from the inputs sequence and run validation.

        NOTE(larsbutler): This code is highly opinionated for bottle, since
        bottle query params are wrapped in a list, even if there is just a
        single value for a given parameter.
        """
        [value] = val
        return volup.Coerce(schema)(value)
    return validate


def coerce_many(schema=str):
    """Expect the input to be a sequence of items which conform to `schema`."""
    def validate(val):
        """Apply schema check/version to each item."""
        return [volup.Coerce(schema)(x) for x in val]
    return validate


def schema(body_schema=None, body_required=False, query_schema=None,  # noqa
           content_types=None, default_body=None):
    """Decorator to parse and validate API body and query string.

    This decorator allows one to define the entire 'schema' for an API
    endpoint.

    :keyword body_schema:
        Callable that accepts raw data and returns the coerced (or unchanged)
        body content if it is valid. Otherwise, an error should be raised.

    :keyword body_required:
        `True` if some body content is required by the request. Defaults to
        `False`.

    :keyword query_schema:
        Callable that accepts raw data and returns the coerced (or unchanged)
        query string content if it is valid. Otherwise, an error should be
        raised.

    :keyword content_types:
        List of allowed contents types for request body contents. Defaults to
        `['application/json']`.

    :keyword default_body:
        Default body value to pass to the endpoint handler if `body_required`
        is `True` but no body was given. This can be useful for specifying
        complex request body defaults.
    """
    if not content_types:
        content_types = ['application/json']
    if not all('json' in t for t in content_types):
        raise NotImplementedError("Only 'json' body supported.")

    def deco(func):
        """Return a decorated callable."""
        def wrapped(*args, **kwargs):
            """Validate/coerce request body and parameters."""
            try:
                # validate the request body per the schema (if applicable):
                try:
                    body = bottle.request.json
                except ValueError as exc:
                    raise simpl_rest.HTTPError(
                        body=str(exc),
                        status=400,
                        exception=exc,
                        traceback=traceback.format_exc(),
                    )
                if body is None:
                    body = default_body
                if body_required and not body:
                    raise simpl_rest.HTTPError(
                        body='Request body cannot be empty.',
                        status=400,
                    )
                if body_schema:
                    try:
                        body = body_schema(body)
                    except volup.MultipleInvalid as exc:
                        raise MultiValidationError(exc.errors)

                # validate the query string per the schema (if application):
                query = bottle.request.query.dict  # pylint: disable=no-member
                if query_schema is not None:
                    try:
                        query = query_schema(query)
                    except volup.MultipleInvalid as exc:
                        raise MultiValidationError(exc.errors)
                if not query:
                    # If the query dict is empty, just set it to None.
                    query = None

                # Conditionally add 'body' or 'schema' to kwargs.
                if any([body_schema, body_required, default_body]):
                    kwargs['body'] = body
                if query_schema:
                    kwargs['query'] = query
                return func(
                    *args,
                    **kwargs
                )
            except MultiValidationError as exc:
                raise simpl_rest.HTTPError(
                    body=str(exc),
                    status=400,
                    exception=exc,
                    traceback=traceback.format_exc(),
                )
        return wrapped
    return deco
