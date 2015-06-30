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

"""REST-ful API Utilites."""

import bottle


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
        def wrapped(*args):
            """Callable to called when the decorated function is called."""
            data = bottle.request.json
            if required and not data:
                bottle.abort(400, "Call body cannot be empty")
            if data is None:
                data = default
            if schema:
                try:
                    data = schema(data)
                except (KeyboardInterrupt, SystemExit):
                    raise  # don't catch and ignore attempts to end the app
                except Exception as exc:
                    bottle.abort(400, str(exc))
            return fxn(data, *args)
        return wrapped
    return wrap
