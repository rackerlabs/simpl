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

import bottle
try:
    import yaml
except ImportError:
    yaml = None

LOG = logging.getLogger(__name__)
MAX_PAGE_SIZE = 10000000
STANDARD_QUERY_PARAMS = ('offset', 'limit', 'sort', 'q', 'facets')


class HTTPError(Exception):

    """Include HTTP Code, description and reason in exception."""

    def __init__(self, message, http_code=400, reason=None):
        """Initialize normal error, but save http code and reason."""
        super(HTTPError, self).__init__(message)
        self.http_code = http_code
        self.reason = reason


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


def error_formatter(error):
    """Bottle error formatter.

    This will take caught errors and output them in our opinionated format and
    the requested media-type. We default to json if we don't recognize or
    support the content.

    The content format is:

        error:             - this is the wrapper for the returned error object
            code:          - the HTTP error code (ex. 404)
            message:       - the HTTP error code message (ex. Not Found)
            description:   - the plain english, user-friendly description. Use
                             this to to surface a UI/CLI. non-technical message
            reason:        - (optional) any additional technical information to
                             help a technical user with troubleshooting

    Usage as a default handler:

        import bottle
        from simple import rest

        app = bottle.default_app()
        app.default_error_handler = rest.error_formatter

        # Meanwhile, elsewhere in a module nearby
        raise rest.HTTPError("Ouch!", http_code=500, reason="Lapse of reason")
    """
    output = {}
    accept = bottle.request.get_header("Accept") or ""
    if "application/x-yaml" in accept:
        error.headers.update({"content-type": "application/x-yaml"})
        writer = functools.partial(yaml.safe_dump, default_flow_style=False)
    else:  # default to JSON
        error.headers.update({"content-type": "application/json"})
        writer = json.dumps

    description = error.body or error.exception
    if isinstance(error.exception, AssertionError):
        error.status = 400
        description = str(error.exception)
        LOG.error(error.exception)
    elif isinstance(error.exception, HTTPError):
        error.status = error.exception.http_code
        description = str(error.exception)
        if error.exception.reason:
            output['reason'] = error.exception.reason
        LOG.error(error.exception)
    elif error.exception:
        error.status = 500
        description = "Unexpected error"

    # Log unexpected args
    if hasattr(error.exception, 'args'):
        if len(error.exception.args) > 1:
            LOG.warning('HTTPError: %s', error.exception.args)

    output['description'] = description
    output['code'] = error.status_code
    output['message'] = error.status_line.split(' ', 1)[1]

    error.apply(bottle.response)
    return writer({'error': output})
