
import re

from .common import *
from ..common import *
from .. import smail
from .open import OpenRegistrar
from .email import EmailRegistrar

__all__ = [ 'ExternalRegistrar' ]

class ExternalRegistrarBase(Registrar):
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

    def _process_new_user(self, uname, uargs, authargs, redirect):
        """Ensure our field shows up in uargs"""
        if not self.required_user_field in uargs:
            raise AuthError("Required field for registration: " + self.required_user_field)
        else:
            userId = uargs[self.required_user_field][0]
            if get_domain(userId) != self.domain:
                raise AuthError("Invalid ID (external domain) for this site")

        self._process_new_user_old(uname, uargs, authargs, redirect)


class ExternalRegistrarNoEmail(ExternalRegistrarBase, OpenRegistrar):
    def __init__(self, conf):
        ExternalRegistrarBase.__init__(self, conf)

class ExternalRegistrarEmail(ExternalRegistrarBase, EmailRegistrar):
    def __init__(self, conf):
        ExternalRegistrarBase.__init__(self, conf)
        EmailRegistrar.__init__(self, conf)
        self.conf['body'] = self.conf['email']['body']
        self.conf['subject'] = self.conf['email']['subject']

def ExternalRegistrar(conf):
    if conf.get('email') is not None:
        return ExternalRegistrarEmail(conf)
    else:
        return ExternalRegistrarNoEmail(conf)

