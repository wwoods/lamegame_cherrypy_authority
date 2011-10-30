import cherrypy
from cherrypy.test.helper import CPWebCase
from unittest import TestCase

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

__all__ = [ 'LgTestCase', 'LgWebCase' ]


class LgTestCase(TestCase):
    def assertGreaterThan(self, expected, actual):
        """Asserts that actual is greater than expected"""
        self.assert_(actual > expected, "{0} > {1}".format(actual, expected))

    def assertLessThan(self, expected, actual):
        """Asserts that actual is less than expected"""
        self.assert_(actual < expected, "{0} < {1}".format(actual, expected))


class LgWebCase(CPWebCase):
    """Exactly the same as CPWebCase, but default behavior is to preserve
    cookies.
    """

    # Make tests fully automatic
    interactive = False

    def __init__(self, *args, **kwargs):
        CPWebCase.__init__(self, *args, **kwargs)
        self.clearCookies()

    def clearCookies(self):
        """Clear out any cookies we were using in our requests."""
        self.cookies = []

    def getPage(self, *args, **kwargs):
        """Open url with debugging support.  Return status, headers, body.
        Automatically sends cookies; clear manually with self.clearCookies().

        Also automatically converts a body passed as a dictionary to url
        params, and appends params to a GET request's url as needed."
        """
        if 'headers' in kwargs:
            kwargs['headers'] += self.cookies
        else:
            kwargs['headers'] = self.cookies

        if 'body' in kwargs:
            body = kwargs['body']
            if isinstance(body, dict):
                kwargs['body'] = urlencode(body)
            if 'method' not in kwargs or kwargs['method'] == 'GET':
                body = kwargs['body']
                del kwargs['body']
                argsList = list(args)
                argsList[0] += '?' + body
                args = tuple(argsList)

        old_cookies = self.cookies
        result = CPWebCase.getPage(self, *args, **kwargs)

        return result

