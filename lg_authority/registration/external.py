
from .common import *
from ..common import *
from .. import smail
from .open import OpenRegistrar
from .email import EmailRegistrar

class ExternalRegistrarBase(Registrar):
    def get_login_url(self):
        """Gets the login url relative to /auth/"""
        if 'open_id' in self.conf:
            return "login_openid?url={0}".format(self.conf['open_id'])
        raise AuthError("Unrecognized external registration")

class ExternalRegistrarNoEmail(ExternalRegistrarBase, OpenRegistrar):
    def __init__(self, conf):
        ExternalRegistrarBase.__init__(self, conf)
    
class ExternalRegistrarEmail(ExternalRegistrarBase, EmailRegistrar):
    def __init__(self, conf):
        EmailRegistrar.__init__(self, conf)
        self.conf['body'] = self.conf['email']['body']
        self.conf['subject'] = self.conf['email']['subject']

def ExternalRegistrar(conf):
    if conf.get('email') is not None:
        return ExternalRegistrarEmail(conf)
    else:
        return ExternalRegistrarNoEmail(conf)

