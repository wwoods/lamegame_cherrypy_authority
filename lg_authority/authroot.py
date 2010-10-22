"""The root for lg_authority web actions"""

import os

import cherrypy

from .common import *
from adminroot import AdminRoot
from openidconsumer import OpenIdConsumerRoot
import passwords

@groups('any')
class AuthRoot(object):
    """The lg_authority class responsible for handling authentication."""

    static = cherrypy.tools.staticdir.handler(
        section='/static'
        ,dir='static'
        ,root=os.path.dirname(os.path.abspath(__file__))
        )

    admin = AdminRoot()

    def __init__(self):
        self.login_openid = OpenIdConsumerRoot(self)

    def login_redirect(self, user, redirect=None):
        """Raises cherrypy.HTTPRedirect to the appropriate location.
        Used by login handlers on success.
        """
        redirect = redirect or config['user_home_page']
        if hasattr(redirect, '__call__'):
            redirect = redirect(user)
        raise cherrypy.HTTPRedirect(redirect)

    @cherrypy.expose
    @groups('auth')
    def index(self):
        return '<div class="lg_auth_form"><p>You are logged in as {user.name}</p><p>You are a member of the following groups: {groups}</p></div>'.format(user=cherrypy.user, groups=get_user_groups_named())

    @cherrypy.expose
    def login(self, **kwargs):
        #Check for already logged in.  This allows page refreshes to login
        #if multiple tabs were open.
        if cherrypy.user:
            self.login_redirect(cherrypy.user, kwargs.get('redirect'))

        kwargs.setdefault('error', '')
        kwargs.setdefault('redirect', '')
        return """
<div class="lg_auth_form">
<span style="color:#ff0000;" class="lg_auth_error">{error}</span>
<form action="login_password" method="POST">
  <input type="hidden" name="redirect" value="{redirect}" />
  <p>
    Password Login:
    <table>
      <tr><td>Username</td><td><input type="text" name="username" /></td></tr>
      <tr><td>Password</td><td><input type="password" name="password" /></td></tr>
      <tr><td><input type="submit" value="Submit" /></td></tr>
    </table>
  </p>
  <p>
    OpenID: 
  </p>
</form>
</div>
        """.format(**kwargs)

    @cherrypy.expose
    def logout(self):
        config.auth.logout()
        redirect = config['logout_page']
        if redirect:
            raise cherrypy.HTTPRedirect(redirect)
        return "You have logged out."

    @cherrypy.expose
    @groups('auth')
    def change_password(self, **kwargs):
        error = ''
        if 'oldpass' in kwargs:
            if not config.auth.test_password(cherrypy.user.name, kwargs['oldpass']):
                error = 'Incorrect password'
            elif kwargs['newpass'] != kwargs['newpass2']:
                error = 'New passwords do not match'
            else:
                new_pass = kwargs['newpass']
                if len(new_pass) < 6:
                    error = 'Password must be 6 or more characters'
                else:
                    config.auth.set_user_password(
                        cherrypy.user.name
                        , [ 'sha256', passwords.sha256(new_pass) ]
                        )
                    return "Password changed successfully."
        return """
<div class="lg_auth_form">
<span style="color:#ff0000;" class="lg_auth_error">{error}</span>
<form action="change_password" method="POST">
  <p>
    Change Password:
    <table>
      <tr><td>Old Password</td><td><input type="password" name="oldpass" /></td></tr>
      <tr><td>New Password</td><td><input type="password" name="newpass" /></td></tr>
      <tr><td>New Password (again)</td><td><input type="password" name="newpass2" /></td></tr>
      <tr><td><input type="submit" value="Submit" /></td></tr>
    </table>
  </p>
</form>
</div>
        """.format(error=error)

    @cherrypy.expose
    @method_filter(methods=['POST'])
    def login_password(self, username, password, redirect=None):
        if config.auth.test_password(username, password):
            user = config.auth.login(username)
            self.login_redirect(user, redirect)
        raise cherrypy.HTTPRedirect(
            url_add_parms(
                'login'
                , { 'error': 'Invalid Credentials', 'redirect': redirect or '' }
                )
            )

    def login_openid_response(self, url, redirect=None, **kwargs):
        """Handles an openid login.  
        This is called directly by a descendent of the AuthRoot path.
        """
        username = config.auth.get_user_from_openid(url)
        if username is not None:
            user = config.auth.login(username)
            self.login_redirect(user, redirect)

        #No known user has that openID... ask if they want to register,
        #if applicable.
        raise cherrypy.HTTPRedirect(
            url_add_parms('../login', { 'error': 'Unknown OpenID: ' + url, redirect: redirect or '' })
            )

