from .common import *
from ..common import *

class AdminRegistrar(Registrar):
    def new_account_ok(self, uname, redirect):
        response = "<p>Registration complete; please wait for administrator approval.</p>"
        if redirect:
            response += '<p>After you have received a notice from the administrator, you may <a href="{0}">Click here to continue</a>'.format(redirect)
        return response

    def process_new_user(self, uname, uargs, authargs, redirect):
        #Enforce that we don't use site_registration_timeout, so that
        #admins on vacation do not lose out on user requests.
        config['site_registration_timeout'] = None
        config.auth.user_create_holder(uname, uargs)

