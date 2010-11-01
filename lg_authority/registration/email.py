import time
from uuid import uuid4

from .common import *
from ..common import *
from .. import smail

class EmailRegistrar(object):
    def __init__(self, conf):
        self.conf = conf

    def new_account_ok(self, uname, redirect):
        return "<p>You will be receiving an email shortly (be sure to check your SPAM folder as well).  Click the link contained in it to activate your account and continue to your original destination.</p>"

    def new_user_fields(self):
        return """<tr><td>Email</td><td><input type="text" style="width:20em;" name="email" /></td></tr>"""

    def process_new_user(self, uname, uargs, authargs, redirect):
        code = uuid4().hex
        email = authargs['email']
        uargs['emails'] = [ email ]
        uargs['email_code'] = code

        #App-level enforcement of no duplicate emails
        #App-level is OK because:
        #1. It can't be a unique index - some auth types don't have email
        #2. There are no security concerns; the user still controls
        #    the email either way if they can register it.
        if len(config.Slate.find_slates_with('user', 'emails', email)) != 0:
            raise AuthError('Email already registered')

        subject = self.conf['subject']
        if hasattr(subject, '__call__'):
            subject = subject(uname)
        body = self.conf['body']
        if hasattr(body, '__call__'):
            body = body(uname)

        body += "\r\n\r\nVisit this address to activate your account: {0}".format(
            url_add_parms(
                cherrypy.url('reg_response_link')
                , { 'key': code, 'username': uname, 'redirect': redirect }
                )
            )

        #Send email
        smail.send_mail(
            email
            ,subject
            ,body
            ,frm=self.conf.get('from')
            )

        #Email sent OK, put in the holder
        config.auth.user_create_holder(uname, uargs)

    def response_link(self, username=None, key=None, redirect=None):
        holder = config.auth.user_get_holder(username)
        if holder is not None and key == holder['email_code']:
            del holder['email_code']
            config.auth.user_promote_holder(holder)
            config.auth.login(username)
            response = "<p>Account activated.  You are now logged in.</p>"
            if redirect:
                response += '<p><a href="{0}">Click to continue</a></p>'.format(redirect)
            return response
        time.sleep(0.1)
        return "Invalid key."

