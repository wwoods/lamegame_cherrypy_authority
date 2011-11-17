
import re

from .common import *
from ..common import *
from .. import smail
from .open import OpenRegistrar

__all__ = [ 'ExternalRegistrar' ]

class ExternalRegistrar(OpenRegistrar):
    def __init__(self, conf):
        Registrar.__init__(self, conf)
        if 'open_id' in self.conf:
            self.required_user_field = 'auth_openid'
            self.domain = get_domain(self.conf['open_id'])
            self.url = "login_openid?url={0}".format(self.conf['open_id'])
        else:
            raise AuthError("Unrecognized external registration")

        self._process_new_user_old = self.process_new_user
        self.process_new_user = self._process_new_user

    def get_login_url(self):
        """Gets the login url relative to /auth/"""
        return self.url

    def new_account_ok(self, uname, redirect):
        # External auth should be transparent; just redirect
        raise cherrypy.HTTPRedirect(redirect)

    def new_user_fields(self, **kwargs):
        return """<tr><td>Email</td><td>
            <input type="text" style="width:20em;" name="email"
                value="{email}"/></td></tr>
            """.format(email=kwargs.get('email') or '')

    def _process_new_user(self, uname, uargs, authargs, redirect):
        """Ensure our fields show up in uargs"""
        email = authargs['email']
        uargs['emails'] = [ email ]

        if not self.required_user_field in uargs:
            raise AuthError(
                "Required field for registration: " 
                + self.required_user_field
            )
        else:
            userId = uargs[self.required_user_field][0]
            if get_domain(userId) != self.domain:
                raise AuthError("Invalid ID (external domain) for this site")

        self._process_new_user_old(uname, uargs, authargs, redirect)


