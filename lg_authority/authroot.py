"""The root for lg_authority web actions"""

import cherrypy

from .common import *
import passwords

def method_filter(methods=['GET','HEAD']):
    """From http://tools.cherrypy.org/wiki/HTTPMethodFiltering"""
    method = cherrypy.request.method.upper()
    if method not in methods:
        cherrypy.response.headers['Allow'] = ', '.join(methods)
        raise cherrypy.HTTPError(405)

method_filter = cherrypy.tools.http_method_filter = cherrypy.Tool('on_start_resource', method_filter)

class AuthRoot(object):
    """The lg_authority class responsible for handling authentication."""

    @cherrypy.expose
    @cherrypy.config(**{ 'tools.lg_authority.groups':[ 'auth' ] })
    def index(self):
        return "Hello, {user.name}!  You are a member of the following groups: {groups}".format(user=cherrypy.user, groups=get_user_groups_named())

    @cherrypy.expose
    def login(self, **kwargs):
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
            redirect = redirect or config['user_home_page']
            if hasattr(redirect, '__call__'):
                redirect = redirect(user)
            raise cherrypy.HTTPRedirect(redirect)
        raise cherrypy.HTTPRedirect(
            url_add_parms(
                'login'
                , { 'error': 'Invalid Credentials', 'redirect': redirect or '' }
                )
            )

