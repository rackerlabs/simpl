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

import functools
import itertools
import json
import logging
import sys
import traceback

import bottle
try:
    import yaml  # pylint: disable=wrong-import-order
except ImportError:
    yaml = None

from simpl.exceptions import SimplHTTPError as HTTPError  # noqa


LOG = logging.getLogger(__name__)
MAX_PAGE_SIZE = 10000000
STANDARD_QUERY_PARAMS = ('offset', 'limit', 'sort', 'q', 'facets')
UNEXPECTED_ERROR = "We're sorry, something went wrong."


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
            try:
                data = bottle.request.json
            except (ValueError, UnicodeDecodeError) as exc:
                bottle.abort(400, str(exc))
            if required and not data:
                bottle.abort(400, "Call body cannot be empty")
            if data is None:
                data = default
            if schema:
                try:
                    data = schema(data)
                except Exception as exc:
                    bottle.abort(400, str(exc))
            return fxn(data, *args, **kwargs)
        return wrapped
    return wrap


def paginated(resource_name=None):
    """Decorator that handles pagination headers, params, and links.

    This accepts, parses, validates, and handles `limit` and `offset` optional
    query params according to common Rackspace APIs and passes them as kwargs
    to the decorated function.

        offset: The pagination offset.
        limit: The pagination limit (or page size). The response is paginated
            with a default limit of 100 and a maximum limit of 1000.

    Headers returned include:
        Content-Range: ... per HTTP RFC and 206 response
        Link: ... one for each page (first, last, next, previous)

    It adds Content-Range headers to the response according to RFC 7233
    section 4.2 - https://tools.ietf.org/html/rfc7233#section-4.2. The resource
    name is supplied in the decorator call as resource_name or deduced from
    uripath if not supplied.

    It adds link headers based on RFC 5988 (by ex-Racker Mark Nottingham) -
    https://tools.ietf.org/html/rfc5988#section-5.5.

    Future changes to the RFCs or common API concepts, such as adding links to
    the response body, may be implemented here to consistently handle
    pagination across all projects using simpl pagination for their APIs.

    Opinionated assumptions:
    - body has data items under a `data` or `results` key.
    - the `len()` of that data represents the number of records being returned
      in this page.
    - body has a `collection-count` value with the total number of records in
      the underlying collection.
    - bottle is being used and this is decorating a route function.

    Responses:
    - paginated responses are returned as `206 Partial Content` unless all the
      data fits in one page, inwhich case the response is `200 OK`.

    Example response for **GET** `/widgets[&limit=2&offset=3]`

    > HTTP/1.0 206 Partial Content
    > Content-Range: widget 3-4/6
    > Content-Length: 217
    > Content-Type: application/json
    > Link: </widgets?limit=2&offset=1>; rel="previous"; title="Previous page"
    > Link: </widgets?limit=2>; rel="first"; title="First page"
    > Link: </widgets?offset=4>; rel="last"; title="Last page"
    ```json
    {
        "collection-count": 6,
        "data": [
            {
                "id": 1,
                "name": "foo"
            },
            {
                "id": 2,
                "name": "bar"
            }
        ]
    }
    ```
    """
    def _paginated(fxn):
        """Add pagination (optional) and headers to response."""
        def _decorator(*args, **kwargs):
            """Internal function wrapped as a decorator."""
            try:
                validate_range_values(bottle.request, 'offset', kwargs)
                validate_range_values(bottle.request, 'limit', kwargs)
            except ValueError:
                bottle.response.status = 416
                bottle.response.set_header(
                    'Content-Range', '%s */*' %
                    resource_name or bottle.request.path.split('/')[-1])
                return

            data = fxn(*args, **kwargs)
            write_pagination_headers(
                data,
                int(kwargs.get('offset') or 0),
                int(kwargs.get('limit') or 100),
                bottle.response,
                bottle.request.path,
                resource_name)
            return data
        return functools.wraps(fxn)(_decorator)
    return _paginated


def validate_range_values(request, label, kwargs):
    """Ensure value contained in label is a positive integer."""
    value = kwargs.get(label, request.query.get(label))
    if value:
        kwargs[label] = int(value)
        if kwargs[label] < 0 or kwargs[label] > MAX_PAGE_SIZE:
            raise ValueError


def write_pagination_headers(data, offset, limit, response, uripath,
                             resource_name):
    """Add pagination headers to the bottle response.

    See docs in :func:`paginated`.
    """
    items = data.get('results') or data.get('data') or {}
    count = len(items)
    try:
        total = int(data['collection-count'])
    except (ValueError, TypeError, KeyError):
        total = None
    if total is None and offset == 0 and (limit is None or limit > len(items)):
        total = count

    # Set 'content-range' header
    response.set_header(
        'Content-Range',
        "%s %d-%d/%s" % (resource_name, offset, offset + max(count - 1, 0),
                         total if total is not None else '*')
    )

    partial = False
    if offset:
        partial = True  # Any offset automatically means we've skipped data
    elif total is None and count == limit:
        # Unknown total, but first page is full (so there may be more)
        partial = True  # maybe more records in next page
    elif total > count:
        # Known total and not all records returned
        partial = True

    if partial:
        uripath = uripath.strip('/')
        response.status = 206  # Partial

        # Add Next page link to http header
        if total is None or (offset + limit) < total - 1:
            nextfmt = (
                '</%s?limit=%d&offset=%d>; rel="next"; title="Next page"')
            response.add_header(
                "Link", nextfmt % (uripath, limit, offset + limit)
            )

        # Add Previous page link to http header
        if offset > 0 and (offset - limit) >= 0:
            prevfmt = ('</%s?limit=%d&offset=%d>; rel="previous"; '
                       'title="Previous page"')
            response.add_header(
                "Link", prevfmt % (uripath, limit, offset - limit)
            )

        # Add first page link to http header
        if offset > 0:
            firstfmt = '</%s?limit=%d>; rel="first"; title="First page"'
            response.add_header(
                "Link", firstfmt % (uripath, limit))

        # Add last page link to http header
        if (total is not None and  # can't calculate last page if unknown total
                limit and  # if no limit, then any page is the last page!
                limit < total):
            lastfmt = '</%s?offset=%d>; rel="last"; title="Last page"'
            if limit and total % limit:
                last_offset = total - (total % limit)
            else:
                last_offset = total - limit
            response.add_header(
                "Link", lastfmt % (uripath, last_offset))


def process_params(request, standard_params=STANDARD_QUERY_PARAMS,
                   filter_fields=None, defaults=None):
    """Parse query params.

    Parses, validates, and converts query into a consistent format.

    :keyword request: the bottle request
    :keyword standard_params: query params that are present in most of our
        (opinionated) APIs (ex. limit, offset, sort, q, and facets)
    :keyword filter_fields: list of field names to allow filtering on
    :keyword defaults: dict of params and their default values
    :retuns: dict of query params with supplied values (string or list)
    """
    if not filter_fields:
        filter_fields = []
    unfilterable = (set(request.query.keys()) - set(filter_fields) -
                    set(standard_params))
    if unfilterable:
        bottle.abort(400,
                     "The following query params were invalid: %s. "
                     "Try one (or more) of %s." %
                     (", ".join(unfilterable),
                      ", ".join(filter_fields)))
    query_fields = defaults or {}
    for key in request.query:
        if key in filter_fields:
            # turns ?netloc=this.com&netloc=that.com,what.net into
            # {'netloc': ['this.com', 'that.com', 'what.net']}
            matches = request.query.getall(key)
            matches = list(itertools.chain(*(k.split(',') for k in matches)))
            if len(matches) > 1:
                query_fields[key] = matches
            else:
                query_fields[key] = matches[0]
    if 'sort' in request.query:
        sort = request.query.getall('sort')
        sort = list(itertools.chain(*(
            comma_separated_strings(str(k)) for k in sort)))
        query_fields['sort'] = sort
    if 'q' in request.query:
        search = request.query.getall('q')
        search = list(itertools.chain(*(
            comma_separated_strings(k) for k in search
            if k)))
        query_fields['q'] = search
    return query_fields


def comma_separated_strings(value):
    """Parse comma-separated string into list."""
    return [str(k).strip() for k in value.split(",")]


def httperror_handler(error):
    """Format error responses properly, return the response body.

    This function can be attached to the Bottle instance as the
    default_error_handler function. It is also used by the
    FormatExceptionMiddleware.
    """
    status_code = error.status_code or 500
    output = {
        'code': status_code,
        'message': error.body or UNEXPECTED_ERROR,
        'reason': bottle.HTTP_CODES.get(status_code) or None,
    }
    if bottle.DEBUG:
        LOG.warning("Debug-mode server is returning traceback and error "
                    "details in the response with a %s status.",
                    error.status_code)
        if error.exception:
            output['exception'] = repr(error.exception)
        else:
            if any(sys.exc_info()):
                output['exception'] = repr(sys.exc_info()[1])
            else:
                output['exception'] = None

        if error.traceback:
            output['traceback'] = error.traceback
        else:
            if any(sys.exc_info()):
                # Otherwise, format_exc() returns "None\n"
                # which is pretty silly.
                output['traceback'] = traceback.format_exc()
            else:
                output['traceback'] = None

    # overwrite previous body attr with json
    if isinstance(output['message'], bytes):
        output['message'] = output['message'].decode(
            'utf-8', errors='replace')

    # Default type and writer to json.
    accept = bottle.request.get_header('accept') or 'application/json'
    writer = functools.partial(
        json.dumps, sort_keys=True, indent=4)
    error.set_header('Content-Type', 'application/json')
    if 'json' not in accept:
        if 'yaml' in accept:
            if not yaml:
                LOG.warning("Yaml requested but pyyaml is not installed.")
            else:
                error.set_header('Content-Type', 'application/x-yaml')
                writer = functools.partial(
                    yaml.safe_dump,
                    default_flow_style=False,
                    indent=4)
            # html could be added here.

    error.body = [writer(output).encode('utf8')]
    return error.body
