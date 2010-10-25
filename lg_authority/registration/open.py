
from ..common import *
from .common import *

class OpenRegistrar(Registrar):
    def new_account_ok(self, uname):
        return "<p>Registration complete.</p>"

    def process_new_user(self, uname, uargs, authargs):
        config.auth.user_create(uname, uargs)
        config.auth.login(uname)

