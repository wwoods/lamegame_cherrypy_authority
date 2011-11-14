
from .common import *
from ..common import *
from .. import smail
from .email import EmailRegistrar

class ExternalRegistrar(EmailRegistrar):
    def get_login_url(self):
        """Gets the login url relative to /auth/"""
        if 'open_id' in self.conf:
            return "login_openid?url={0}".format(self.conf['open_id'])
        raise AuthError("Unrecognized external registration")

