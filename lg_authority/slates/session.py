"""The session functionality of lg_authority/slates.
"""

import os
import datetime
import time
import binascii
from cherrypy.lib import httputil
import cherrypy
from ..common import *
from .slates import Slate

class Session(Slate):
    """A container that maps session ID's to an underlying slate."""

    session_cookie = 'session_id'
    session_cookie__doc = """Name of cookie where session id is stored"""

    timeout=60
    timeout__doc = """Timeout (in minutes) until session expiration"""

    originalid = None
    originalid__doc = """Client-sent identifier for the session slate"""

    def __init__(self, id=None, **kwargs):
        self.timeout = kwargs.pop('session_timeout', Session.timeout) * 60
        self.session_cookie = kwargs.get('session_cookie', self.session_cookie)

        self.originalid = id
        self.id = id
        #Check for expired session, and assign new identifier if
        #necessary.  _test_id calls Slate.__init__
        self._test_id()

        if not self.is_expired():
            #Check for the need to update the session's expiration date.
            #Update if we're either halfway through our session timeout or
            #at one hour intervals, whichever comes first.
            #Remember that by this point, timeout is in seconds instead of
            #minutes.
            ttl = self.time_to_expire()
            if ttl < self.timeout // 2 or ttl < self.timeout - 60*60:
                self.touch()
                self._update_cookie = True
        else:
            #This is a brand new session.  We should probably
            #touch it to prevent it from expiring.  We could just send a 
            #new session ID on each request, like the default CherryPy 
            #behavior, but for an application with AJAX login this 
            #can cause very weird issues.
            self.touch()
            self._update_cookie = True

        #The response cookie is set in send_session_cookie(), at the bottom of this
        #file.

    def is_response_cookie_needed(self):
        #Turns out, a lot of caching mechanisms determine whether to cache
        #or not based on whether or not the response contains a cookie.
        #It's best to always return one.
        return True

        if self.id != self.originalid:
            return True
        if hasattr(self, '_update_cookie'):
            return True
        return False

    def expire(self):
        """Expires the session both client-side and slate-side"""
        Slate.expire(self)

        one_year = 60 * 60 * 24 * 365
        e = time.time() - one_year
        cherrypy.serving.response.cookie[self.session_cookie] = 'expired'
        cherrypy.serving.response.cookie[self.session_cookie]['expires'] = httputil.HTTPDate(e)

    def regen_id(self):
        """Copies all of the data for this cookie, but regenerates
        it under a new identifier.  Some sources recommend changing 
        session id on login, and that is what this does.  Essentially
        prevents an attacker from creating a blank, persistent session,
        getting a user to log in through whatever means, and then 
        using the previously blank session as a logged in session of
        the victim.
        """
        data = self.todict()
        Slate.expire(self)
        self._test_id()
        self.update(data)
        self._update_cookie = True

    def _test_id(self):
        """Test if we are expired.  If we are, assign a new id"""
        #Force the session timeout to always update with the site's preferences.
        new_timeout = self.timeout
        Slate.__init__(
            self
            , 'session'
            , self.id
            , timeout=new_timeout
            , force_timeout=True
            )
        if self.is_expired():
            while True:
                self.id = self._generate_id()
                #We are looking for expired (non-existant) sessions, so no
                #need to set force_timeout
                Slate.__init__(self, 'session', self.id, timeout=new_timeout)
                if self.is_expired():
                    break
            log('Session {0} expired -> {1}'.format(self.originalid, self.id))

    def _generate_id(self):
        """Return a new session id."""
        return binascii.hexlify(os.urandom(20)).decode('ascii')
    
def init_session(
    session_path=None
    , session_path_header=None
    , session_domain=None
    , session_secure=False
    , session_httponly=True
    , session_persistent=True
    , **kwargs
    ):
    """Initialize session object (using cookies).  
    Attached to before_request_body.
    
    session_path: the 'path' value to stick in the response cookie metadata.
    session_path_header: if 'path' is None (the default), then the response
        cookie 'path' will be pulled from request.headers[path_header].
    session_cookie: the name of the cookie.
    session_timeout: the expiration timeout (in minutes) for the stored session 
        data. If 'persistent' is True (the default), this is also the timeout
        for the cookie.
    session_domain: the cookie domain.
    session_secure: if False (the default) the cookie 'secure' value will not
        be set. If True, the cookie 'secure' value will be set (to 1).
    session_httponly: If True (the default) the cookie 'httponly' value will be
        set, which prevents client scripts from reading the cookie.  This
        helps to guard against XSS.
    session_persistent: if True (the default), the 'timeout' argument will be 
        used to expire the cookie. If False, the cookie will not have an expiry,
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
    cookie_timeout = kwargs.get('session_timeout', Session.timeout)
    
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
    
def send_session_cookie(
    session_path=None
    , session_path_header=None
    , session_domain=None
    , session_secure=False
    , session_httponly=True
    , session_persistent=True
    , **kwargs
    ):
    """Send the session cookie after the body in case the request
    regenerated the session id and it needs to be retransmitted.
    """
    sess = cherrypy.serving.session
    if sess.is_response_cookie_needed():
        session_cookie = kwargs.get('session_cookie', Session.session_cookie)
        cookie_timeout = kwargs.get('session_timeout', Session.timeout)
        if not session_persistent:
            # See http://support.microsoft.com/kb/223799/EN-US/
            # and http://support.mozilla.com/en-US/kb/Cookies
            cookie_timeout = None
        set_response_cookie(
          path=session_path, path_header=session_path_header
          , name=session_cookie
          , timeout=cookie_timeout
          , domain=session_domain
          , secure=session_secure
          , httponly=session_httponly
          )


def set_response_cookie(path=None, path_header=None, name='session_id',
                        timeout=60, domain=None, secure=False, httponly=True):
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
    httponly: if True (the default) the cookie's 'httponly' value will be
        set, preventing client scripts from reading the cookie.  Helps prevent
        XSS, see https://www.owasp.org/index.php/HttpOnly
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
    if httponly:
        cookie[name]['httponly'] = 1

