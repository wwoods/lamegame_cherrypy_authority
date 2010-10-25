from .common import *
from ..common import *

class AdminRegistrar(Registrar):
    def new_account_ok(self, uname):
        return "<p>Registration complete; please wait for administrator approval.</p>"

    def process_new_user(self, uname, uargs, authargs):
        #Enforce that we don't use site_registration_timeout, so that
        #admins on vacation do not lose out on user requests.
        config['site_registration_timeout'] = None
        config.auth.user_create_holder(uname, uargs)

