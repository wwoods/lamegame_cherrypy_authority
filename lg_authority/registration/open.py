
from ..common import *
from .common import *

class OpenRegistrar(Registrar):
    def new_account_ok(self, uname, redirect):
        response = "<p>Registration complete.</p>"
        if redirect:
            response += '<p><a href="{0}">Click here to continue</a></p>'.format(redirect)
        return response

    def process_new_user(self, uname, uargs, authargs, redirect):
        config.auth.user_create(uname, uargs)
        config.auth.login(uname)

