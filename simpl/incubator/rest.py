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

import bottle
import six
import voluptuous as volup


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


def query(schema=None):
    """Decorator to parse and validate API query string.

    This decorator allows one to define the entire 'schema' for an API
    endpoint.

    :keyword query_schema:
        Callable that accepts raw data and returns the coerced (or unchanged)
        query string content if it is valid. Otherwise, an error should be
        raised.
    """
    def deco(func):
        """Return a decorated callable."""
        def wrapped(*args, **kwargs):
            """Validate/coerce request query parameters."""
            try:
                # validate the query string per the schema (if application):
                query = bottle.request.query.dict
                if query_schema is not None:
                    try:
                        query = schema(query)
                    except volup.MultipleInvalid as exc:
                        raise MultiValidationError(exc.errors)

                # Assign the possibly-modified query back the bottle request
                # query object.
                bottle.request.query = bottle.FormsDict(query)

                return func(
                    *args,
                    **kwargs
                )
            except Exception as exc:
                bottle.abort(400, str(exc))
        return wrapped
    return deco


def body(schema=None, types=None, required=False, default=None):
    """Decorator to parse and validate API body.

    :keyword schema: callable that accepts raw data and returns the coerced (or
        unchanged) data if it is valid. It should raise an error if the data is
        not valid.
    :keyword types: supported content types (default is ['application/json'])
    :keyword required: if true and no body specified will raise an error.
    :keyword default: default value to return if no body supplied

    Note: only json types are supported.
    """
    if not types:
        types = ['application/json']
    if not all('json' in t for t in types):
        raise NotImplementedError("Only 'json' body supported.")

    def wrap(fxn):
        """Return a decorated callable."""
        def wrapped(*args, **kwargs):
            """Callable to called when the decorated function is called."""
            body = bottle.request.json
            if required and not body:
                bottle.abort(400, "Call body cannot be empty")
            if body is None:
                body = default
            if schema:
                try:
                    body = schema(body)
                except (KeyboardInterrupt, SystemExit):
                    raise  # don't catch and ignore attempts to end the app
                except Exception as exc:
                    bottle.abort(400, str(exc))
            # Once we've validate and possible updated the request body
            # contents, slap it back onto the request.
            bottle.request.json = body
            return fxn(*args, **kwargs)
        return wrapped
    return wrap
