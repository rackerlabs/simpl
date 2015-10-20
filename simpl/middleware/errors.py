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

"""Middleware for errors and exceptions.

Example:

    # Allow this middleware to catch, handle and format all errors.

    import bottle
    from simpl.middleware import errors

    app = bottle.default_app()
    app.catchall = False
    # To catch errors that occur in other middleware...
    app = FormatExceptionMiddleware(app)
    # Tell bottle to use rest.httperror_handler when
    # handling its own bottle.HTTPErrors
    app.default_error_handler = rest.httperror_handler
    bottle.run(app=app)


    Example responses (the following use catchall=False)
    -----------------------------------------------------

    An unexpected error if the server is in debug mode:

        # raise TypeError('Poor type choice.')
        {
            "code": 500,
            "exception": "TypeError('Poor type choice.',)",
            "message": "We're sorry, something went wrong.",
            "reason": "Internal Server Error",
            "traceback": "Traceback (most recent call last): ... ",
        }

    An "expected" error if the server is in debug mode:

        # raise SimplHTTPError(body='Hey!', status=405)
        {
            "code": 405,
            "exception": "SimplHTTPError('Hey!',)",
            "message": "Hey!",
            "reason": "Method Not Allowed",
            "traceback": "Traceback (most recent call last): ..."
        }

    Unexpected error without debug mode:

        # raise TypeError('Poor type choice.')
        {
            "code": 500,
            "message": "We're sorry, something went wrong.",
            "reason": "Internal Server Error"
        }

    An "expected" error without debug mode:

        # raise SimplHTTPError(body='Hey!', status=405)
        {
            "code": 405,
            "message": "Hey!",
            "reason": "Method Not Allowed"
        }
"""
from __future__ import print_function

import logging
import sys
import traceback

import bottle

from simpl import exceptions
from simpl import rest

LOG = logging.getLogger(__name__)


def _catchall_enabled(app):
    """Check the bottle app for catchall."""
    while hasattr(app, 'app'):
        if isinstance(app, bottle.Bottle):
            break
        app = app.app
    if hasattr(app, 'catchall'):
        return app.catchall
    else:
        return bottle.default_app().catchall


class FormatExceptionMiddleware(object):

    """Format outgoing exceptions.

    Uses and is compatible-with bottle exception formatting.

    - Handle Bottle Exceptions (even when catchall=False).
    - Handle SimplHTTPError
    - Fail-safe to a generic error (unexpected_error)

    The code in this middleware is meant to be generic.
    Don't catch and translate fancy exceptions here, do
    it in the application logic or a separate middleware and
    raise a bottle.HTTPError or a SimplHTTPError.
    """

    def __init__(self, app, conf=None):
        """Initialize class."""
        if _catchall_enabled(app) is True:
            LOG.warning("Bottle's catchall flag is enabled for your app. "
                        "The suggested use for this middleware is with "
                        "catchall disabled, otherwise bottle will overwrite "
                        "the exception context, sys.exc_info() and raise a "
                        "bottle.HTTPError instead, which renders the error "
                        "handling middleware less useful and less flexible.")
        self.app = app
        self.config = conf
        LOG.debug("Added middleware: %s", type(self).__name__)

    def __call__(self, environ, start_response):
        """Catch exceptions and format them based on config."""
        try:
            return self.app(environ, start_response)
        except bottle.HTTPError as error:
            LOG.error("Formatting a bottle exception.",
                      exc_info=error)

            rest.httperror_handler(error)
            start_response(error.status_line, error.headerlist)
            return error
        except exceptions.SimplHTTPError as error:
            LOG.error("Formatting a SimplHTTPError exception.",
                      exc_info=error)
            error = bottle.HTTPError(
                status=error.status_code, body=error.body,
                exception=error.exception or error,
                traceback=error.traceback or traceback.format_exc())
            rest.httperror_handler(error)
            start_response(error.status_line, error.headerlist)
            return error
        except Exception as error:  # pylint: disable=W0703
            LOG.error("Formatting an unexpected exception.",
                      exc_info=error)
            error = bottle.HTTPError(
                status=500, body=rest.UNEXPECTED_ERROR,
                exception=error,
                traceback=traceback.format_exc())
            rest.httperror_handler(error)
            start_response(error.status_line, error.headerlist)
            return error
        except:  # noqa
            LOG.error("Formatting an unknown exception.",
                      exc_info=True)
            error = bottle.HTTPError(
                status=500, body=rest.UNEXPECTED_ERROR,
                exception=sys.exc_info()[1],
                traceback=traceback.format_exc())
            rest.httperror_handler(error)
            start_response(error.status_line, error.headerlist)
            return error
