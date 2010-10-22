"""The session functionality of lg_authority/slates."""

import os
import datetime
import binascii
import cherrypy
from ..common import *
from .slates import Slate

class Session(Slate):
    """A container that maps session ID's to an underlying slate."""

    id = None
    id__doc = """Session id.  Use Session.get_slate_name(id) to get the name of a slate with the specified id."""

    session_cookie = 'session_id'
    session_cookie__doc = """Name of cookie where session id is stored"""

    timeout=60
    timeout__doc = """Timeout (in minutes) until session expiration"""

    originalid = None
    originalid__doc = """Client-sent identifier for the session slate"""

    def __init__(self, id=None, **kwargs):
        self.timeout = kwargs.pop('session_timeout', self.timeout)
        self.session_cookie = kwargs.get('session_cookie', self.session_cookie)

        self.originalid = id
        self.id = id
        #Check for expired session, and assign new identifier if
        #necessary.
        self._test_id()

        Slate.__init__(self, self.get_slate_name(), timeout=self.timeout)

        #The response cookie is set in init_session(), at the bottom of this
        #file.

    def expire(self):
        """Expires the session both client-side and slate-side"""
        Slate.expire(self)

        one_year = 60 * 60 * 24 * 365
        e = time.time() - one_year
        cherrypy.serving.response.cookie[self.session_cookie]['expires'] = httputil.HTTPDate(e)

    def get_slate_name(self):
        """Returns the slate name for this session id"""
        return 'session-' + self.id

    def _test_id(self):
        """Test if we are expired.  If we are, assign a new id"""
        if self.id is None or self._is_expired():
            while True:
                self.id = self._generate_id()
                if self._is_expired():
                    break
            log('Session {0} expired -> {1}'.format(self.originalid, self.id))

    def _is_expired(self):
        return Slate.is_expired(self.get_slate_name())
        
    def _generate_id(self):
        """Return a new session id."""
        return binascii.hexlify(os.urandom(20)).decode('ascii')
    
def init_session(
    session_path=None
    , session_path_header=None
    , session_domain=None
    , session_secure=False
    , session_persistent=True
    , **kwargs
    ):
    """Initialize session object (using cookies).
    
    storage_type: one of 'ram', 'file', 'postgresql'. This will be used
        to look up the corresponding class in cherrypy.lib.sessions
        globals. For example, 'file' will use the FileSession class.
    path: the 'path' value to stick in the response cookie metadata.
    path_header: if 'path' is None (the default), then the response
        cookie 'path' will be pulled from request.headers[path_header].
    name: the name of the cookie.
    timeout: the expiration timeout (in minutes) for the stored session data.
        If 'persistent' is True (the default), this is also the timeout
        for the cookie.
    domain: the cookie domain.
    secure: if False (the default) the cookie 'secure' value will not
        be set. If True, the cookie 'secure' value will be set (to 1).
    clean_freq (minutes): the poll rate for expired session cleanup.
    persistent: if True (the default), the 'timeout' argument will be used
        to expire the cookie. If False, the cookie will not have an expiry,
        and the cookie will be a "session cookie" which expires when the
        browser is closed.
    
    Any additional kwargs will be bound to the new Session instance,
    and may be specific to the storage type. See the subclass of Session
    you're using for more information.
    """
    
    # Guard against running twice
    if hasattr(cherrypy.serving, "session"):
        return
    
    request = cherrypy.serving.request
    name = session_cookie = kwargs.get('session_cookie', Session.session_cookie)
    cookie_timeout = kwargs.get('session_timeout', None)
    
    # Check if request came with a session ID
    id = None
    if session_cookie in request.cookie:
        id = request.cookie[session_cookie].value
        log('ID obtained from request.cookie: %r' % id)
    else:
        log('New session (no cookie)')
    
    # Create and attach a new Session instance to cherrypy.serving.
    # It will possess a reference to (and lock, and lazily load)
    # the requested session data.
    cherrypy.serving.session = sess = Session(id, **kwargs)
    
    if not session_persistent:
        # See http://support.microsoft.com/kb/223799/EN-US/
        # and http://support.mozilla.com/en-US/kb/Cookies
        cookie_timeout = None
    set_response_cookie(path=session_path, path_header=session_path_header
      , name=name
      , timeout=cookie_timeout, domain=session_domain, secure=session_secure)


def set_response_cookie(path=None, path_header=None, name='session_id',
                        timeout=60, domain=None, secure=False):
    """Set a response cookie for the client.
    
    path: the 'path' value to stick in the response cookie metadata.
    path_header: if 'path' is None (the default), then the response
        cookie 'path' will be pulled from request.headers[path_header].
    name: the name of the cookie.
    timeout: the expiration timeout for the cookie. If 0 or other boolean
        False, no 'expires' param will be set, and the cookie will be a
        "session cookie" which expires when the browser is closed.
    domain: the cookie domain.
    secure: if False (the default) the cookie 'secure' value will not
        be set. If True, the cookie 'secure' value will be set (to 1).
    """
    # Set response cookie
    cookie = cherrypy.serving.response.cookie
    cookie[name] = cherrypy.serving.session.id
    cookie[name]['path'] = (path or cherrypy.serving.request.headers.get(path_header)
                            or '/')
    
    # We'd like to use the "max-age" param as indicated in
    # http://www.faqs.org/rfcs/rfc2109.html but IE doesn't
    # save it to disk and the session is lost if people close
    # the browser. So we have to use the old "expires" ... sigh ...
##    cookie[name]['max-age'] = timeout * 60
    if timeout:
        e = time.time() + (timeout * 60)
        cookie[name]['expires'] = httputil.HTTPDate(e)
    if domain is not None:
        cookie[name]['domain'] = domain
    if secure:
        cookie[name]['secure'] = 1
