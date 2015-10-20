"""Test FormatExceptionMiddleware."""

import unittest

import bottle
import webtest
import yaml

from simpl import exceptions as simpl_exc
from simpl.middleware import errors as errors_middleware
from simpl import rest


class TestFmtExcMiddleware(unittest.TestCase):

    """Test logs and responses when Exception Middleware is enabled."""

    @classmethod
    def setUpClass(cls):
        """Init the tests by starting the bottle app and routes."""
        super(TestFmtExcMiddleware, cls).setUpClass()

        app = bottle.default_app()
        app.catchall = False
        app.default_error_handler = rest.format_error_response

        def unexpected_error():
            raise Exception("My logic is bad.")
        app.route(path='/unexpected_error', method='GET',
                  callback=unexpected_error)

        def keyboard():
            raise KeyboardInterrupt("A funny signal.")
        app.route(path='/keyboard', method='GET',
                  callback=keyboard)

        def simpl_500():
            raise simpl_exc.SimplHTTPError(body="Help.", status=500)
        app.route(path='/simpl_500', method='GET', callback=simpl_500)

        def simpl_500_alt():
            raise rest.HTTPError("And I feel bad.", status=500)
        app.route(path='/simpl_500_alt', method='GET', callback=simpl_500_alt)

        def bottle_500():
            raise bottle.HTTPError(body="Not sorry.", status=500)
        app.route(path='/bottle_500', method='GET', callback=bottle_500)

        def simpl_403():
            raise simpl_exc.SimplHTTPError(body="Rejected.", status=403)
        app.route(path='/simpl_403', method='GET',
                  callback=simpl_403)

        app = errors_middleware.FormatExceptionMiddleware(app)
        cls.app = webtest.TestApp(app)

    def test_unexpected_error_debug(self):
        bottle.debug(True)
        resp = self.app.get('/unexpected_error', expect_errors=True)
        bottle.debug(False)
        self.assertEqual(resp.status_code, 500)
        self.assertIn('reason', resp.json_body)
        self.assertIn('code', resp.json_body)
        self.assertIn('message', resp.json_body)
        self.assertIn('exception', resp.json_body)
        self.assertIn('traceback', resp.json_body)
        self.assertEqual(
            len(resp.json_body['traceback'].splitlines()),
            14
        )
        self.assertEqual(
            resp.json_body['exception'],
            "Exception('My logic is bad.',)"
        )
        self.assertEqual(
            resp.json_body['message'],
            "We're sorry, something went wrong."
        )
        self.assertEqual(
            resp.json_body['reason'],
            "Internal Server Error"
        )
        self.assertEqual(
            resp.json_body['code'],
            500
        )

    def test_unexpected_error(self):
        resp = self.app.get('/unexpected_error', expect_errors=True)
        self.assertEqual(resp.status_code, 500)
        self.assertIn('reason', resp.json_body)
        self.assertIn('code', resp.json_body)
        self.assertIn('message', resp.json_body)
        self.assertEqual(
            resp.json_body['message'],
            "We're sorry, something went wrong."
        )
        self.assertEqual(
            resp.json_body['reason'],
            "Internal Server Error"
        )
        self.assertEqual(
            resp.json_body['code'],
            500
        )

    def test_keyboard(self):
        resp = self.app.get('/keyboard', expect_errors=True)
        self.assertEqual(resp.status_code, 500)
        self.assertIn('reason', resp.json_body)
        self.assertIn('code', resp.json_body)
        self.assertIn('message', resp.json_body)
        self.assertEqual(
            resp.json_body['message'],
            "We're sorry, something went wrong."
        )
        self.assertEqual(
            resp.json_body['reason'],
            "Internal Server Error"
        )
        self.assertEqual(
            resp.json_body['code'],
            500
        )

    def test_keyboard_debug(self):
        bottle.debug(True)
        resp = self.app.get('/keyboard', expect_errors=True)
        bottle.debug(False)
        self.assertEqual(resp.status_code, 500)
        self.assertIn('reason', resp.json_body)
        self.assertIn('code', resp.json_body)
        self.assertIn('message', resp.json_body)
        self.assertIn('exception', resp.json_body)
        self.assertIn('traceback', resp.json_body)
        self.assertEqual(
            len(resp.json_body['traceback'].splitlines()),
            14
        )
        self.assertEqual(
            resp.json_body['exception'],
            "KeyboardInterrupt('A funny signal.',)"
        )
        self.assertEqual(
            resp.json_body['message'],
            "We're sorry, something went wrong."
        )
        self.assertEqual(
            resp.json_body['reason'],
            "Internal Server Error"
        )
        self.assertEqual(
            resp.json_body['code'],
            500
        )

    def test_unexpected_error_yaml(self):
        resp = self.app.get(
            '/unexpected_error',
            expect_errors=True,
            headers={'Accept': 'application/x-yaml'}
        )
        self.assertEqual(resp.status_code, 500)
        yaml_body = yaml.safe_load(resp.body)
        self.assertIn('reason', yaml_body)
        self.assertIn('code', yaml_body)
        self.assertIn('message', yaml_body)
        self.assertEqual(
            yaml_body['message'],
            "We're sorry, something went wrong."
        )
        self.assertEqual(
            yaml_body['reason'],
            "Internal Server Error"
        )
        self.assertEqual(
            yaml_body['code'],
            500
        )

    def test_simpl_500(self):
        resp = self.app.get('/simpl_500', expect_errors=True)
        self.assertEqual(resp.status_code, 500)
        self.assertIn('reason', resp.json_body)
        self.assertIn('code', resp.json_body)
        self.assertIn('message', resp.json_body)
        self.assertEqual(
            resp.json_body['message'],
            "Help."
        )
        self.assertEqual(
            resp.json_body['reason'],
            "Internal Server Error"
        )
        self.assertEqual(
            resp.json_body['code'],
            500
        )

    def test_simpl_500_alt(self):
        resp = self.app.get('/simpl_500_alt', expect_errors=True)
        self.assertEqual(resp.status_code, 500)
        self.assertIn('reason', resp.json_body)
        self.assertIn('code', resp.json_body)
        self.assertIn('message', resp.json_body)
        self.assertEqual(
            resp.json_body['message'],
            "We're sorry, something went wrong."
        )
        self.assertEqual(
            resp.json_body['reason'],
            "Internal Server Error"
        )
        self.assertEqual(
            resp.json_body['code'],
            500
        )

    def test_bottle_500(self):
        resp = self.app.get('/bottle_500', expect_errors=True)
        self.assertEqual(resp.status_code, 500)
        self.assertIn('reason', resp.json_body)
        self.assertIn('code', resp.json_body)
        self.assertIn('message', resp.json_body)
        self.assertEqual(
            resp.json_body['message'],
            "Not sorry."
        )
        self.assertEqual(
            resp.json_body['reason'],
            "Internal Server Error"
        )
        self.assertEqual(
            resp.json_body['code'],
            500
        )

    def test_simpl_403(self):
        resp = self.app.get('/simpl_403', expect_errors=True)
        self.assertEqual(resp.status_code, 403)
        self.assertIn('reason', resp.json_body)
        self.assertIn('code', resp.json_body)
        self.assertIn('message', resp.json_body)
        self.assertEqual(
            resp.json_body['message'],
            "Rejected."
        )
        self.assertEqual(
            resp.json_body['reason'],
            "Forbidden"
        )
        self.assertEqual(
            resp.json_body['code'],
            403
        )


class WorstMiddlewareEver(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        raise Exception("Bugs!")


class TestFmtExcMiddlewareAlt(unittest.TestCase):

    """Tests FormatExceptionMiddleware works when other middleware fails."""

    @classmethod
    def setUpClass(cls):
        """Init the tests by starting the bottle app and routes."""
        super(TestFmtExcMiddlewareAlt, cls).setUpClass()

        app = bottle.default_app()
        app.catchall = False
        app.default_error_handler = rest.format_error_response

        app.route(path='/', method='GET',
                  callback=lambda: 'Hello')

        app = WorstMiddlewareEver(app)
        app = errors_middleware.FormatExceptionMiddleware(app)
        cls.app = webtest.TestApp(app)

    def setUp(self):
        # Something weird is going on with bottle's threadlocals.
        bottle.request.environ.clear()

    def test_worst_middleware(self):
        bottle.debug(True)
        resp = self.app.get('/', expect_errors=True)
        bottle.debug(False)
        self.assertEqual(resp.status_code, 500)
        self.assertIn('reason', resp.json_body)
        self.assertIn('code', resp.json_body)
        self.assertIn('message', resp.json_body)
        self.assertIn('exception', resp.json_body)
        self.assertIn('traceback', resp.json_body)
        self.assertEqual(
            len(resp.json_body['traceback'].splitlines()),
            6
        )
        self.assertEqual(
            resp.json_body['exception'],
            "Exception('Bugs!',)"
        )
        self.assertEqual(
            resp.json_body['message'],
            "We're sorry, something went wrong."
        )
        self.assertEqual(
            resp.json_body['reason'],
            "Internal Server Error"
        )
        self.assertEqual(
            resp.json_body['code'],
            500
        )


if __name__ == '__main__':
    unittest.main()
