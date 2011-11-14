"""The root for lg_authority web actions"""

import os
import datetime
import json

import cherrypy

from .common import *
from .controls import *
from .adminroot import AdminRoot
from .openidconsumer import OpenIdConsumerRoot
from .openidserver import OpenIdServerRoot
from . import passwords

@groups('any')
class AuthRoot(object):
    """The lg_authority class responsible for handling authentication."""
    
    _cp_config = {
        "response.headers.Content-Type": "text/html"
    }

    static = cherrypy.tools.staticdir.handler(
        section='/static'
        ,dir='static'
        ,root=os.path.dirname(os.path.abspath(__file__))
        )

    admin = AdminRoot()

    def __init__(self):
        self.login_openid = OpenIdConsumerRoot(self)
        self.openid = OpenIdServerRoot(self)

    def login_redirect(self, redirect=None):
        """Raises cherrypy.HTTPRedirect to the appropriate location.
        Used by login handlers on success.
        """
        redirect = redirect or config['user_home_page']
        if hasattr(redirect, '__call__'):
             redirect = redirect()
        if cherrypy.user.isOldPassword():
            redirect = url_add_parms(
                'change_password'
                , { 'redirect': redirect, 'error': 'Your password is more than {old} days old.  It would be good to change it for security.'.format(old=config['site_password_renewal']) }
                )
        raise cherrypy.HTTPRedirect(redirect)

    @cherrypy.expose
    @groups('auth')
    def index(self):
        p = LgPageControl()
        p.append('<p>You are logged in as ', TextControl(cherrypy.user.id), '</p>')
        g = GenericControl(
            '<p>You are a member of the following groups: {children}</p>'
            , child_wrapper = [ '', ', ', '' ]
            ).appendto(p)
        g.extend([ TextControl(g[1]) for g in get_user_groups_named().items() ])
        p.append('<p><a href="change_password">Change Password</a></p>')
        if 'admin' in cherrypy.user.groups:
            p.append('<p><a href="admin/">Admin Interface</a></p>')
        return p.gethtml()
        body = []
        body.append('<div class="lg_auth_form">')
        body.append('<p>You are logged in as {user.id} <a href="logout">(logout)</a></p><p>You are a member of the following groups: {groups}</p>'.format(
            user=cherrypy.user
            , groups=[ g[1] for g in get_user_groups_named().items() ]
            ))
        body.append('<p><a href="change_password">Change Password</a></p>')
        if 'admin' in cherrypy.user.groups:
            body.append('<p><a href="admin/">Admin Interface</a></p>')
        body.append('</div>')
        return ''.join(body)

    @cherrypy.expose
    @cherrypy.config(**{'response.headers.Content-Type': 'text/plain'})
    def login_service(self, **kwargs):
        if 'username' in kwargs:
            username = kwargs['username'].lower()
            password = kwargs['password']

            #TODO - this is horribly wrong.  we shouldn't be logging in the user
            #just to get their information and forward it.
            userid = config.auth.test_password(username, password)
            if username is not None:
                user = config.auth.login(userid)
            
        if cherrypy.user:
            #Filter out any, auth group from this list.  Leave that up
            #to the application using the login service.
            groups = [ { 'id': k, 'name': v } for k,v in get_user_groups_named().items() if k != 'any' and k != 'auth']
            return json.dumps({ 
                'username': cherrypy.user.id
                ,'userprimary': 'user-' + cherrypy.user.id
                ,'usergroups': groups
                })
        return json.dumps({ 'error': 'Invalid credentials' })

    @cherrypy.expose
    def login(self, **kwargs):
        #Check for already logged in.  This allows page refreshes to login
        #if multiple tabs were open.
        if cherrypy.user and 'admin' not in kwargs:
            self.login_redirect(kwargs.get('redirect'))

        if config['site_registration'] == 'external':
            #Forward login page to appropriate handler
            url = config.registrar.get_login_url()
            url += "&redirect={0}".format(kwargs.get('redirect'))
            raise cherrypy.HTTPRedirect(url)

        kwargs.setdefault('error', '')
        kwargs.setdefault('redirect', '')
        if config['site_registration'] is None:
            kwargs['new_account'] = """<p class="lg_auth_newaccount">
New accounts are not allowed.  Contact administrator if you need access.
</p>"""
        else:
            kwargs['new_account'] = """<p class="lg_auth_newaccount">
<a href="{0}">Don't have an account here?  Create one.</a>
</p>""".format(url_add_parms('new_account', { 'redirect': kwargs.get('redirect', '') }))

        forgot = ''
        if config['site_email'] is not None:
            forgot = '<tr><td><a href="{forgot_link}">Forgot your password?</a></td></tr>'.format(
                forgot_link=url_add_parms('forgot_password', { 'redirect': kwargs.get('redirect') })
                )

        password_form = """
<form action="login_password{adminqs}" method="POST">
  <input type="hidden" name="redirect" value="{redirect}" />
  <p>
    Password Login:
    <table>
      <tr><td>Username or Email</td><td><input type="text" name="username" /></td></tr>
      <tr><td>Password</td><td><input type="password" name="password" /></td></tr>
      <tr><td><input type="submit" value="Submit" /></td></tr>
      {forgot}
    </table>
  </p>
</form>""".format(
            redirect=kwargs.get('redirect', '')
            , forgot=forgot
            , adminqs='?admin=true' if 'admin' in kwargs else ''
            )

        openid_form = ''
        if self.login_openid.supported:
            #Setup OpenID providers
            openid_list = []
            def add_provider(name, url):
                prov_parms = {
                    'url': url
                    ,'redirect': kwargs['redirect']
                    }
                if 'admin' in kwargs:
                    prov_parms['admin'] = 'true'
                li = """<li><a href="{url}">{name}</a></li>""".format(
                    url = url_add_parms('login_openid', prov_parms)
                    ,name = name
                    )
                openid_list.append(li)

            add_provider('Google', 'https://www.google.com/accounts/o8/id')
            add_provider('Yahoo!', 'http://yahoo.com')
            openid_list.append("""<li><form method="GET" action="login_openid" class="lg_auth_openid_><input type="hidden" name="redirect" value="{redirect}"/>OpenID URL: <input style="width:20em;" type="text" name="url" value="http://"/><input type="submit" value="Submit"/></form></li>""".format(**kwargs))
            openid_list = ''.join(openid_list)
            openid_form = """
<p class="lg_auth_select_openid">
  OpenID (have an account with any of these providers?  Click the appropriate icon to use it here):<ul>
    {openid_list}
  </ul>
</p>""".format(openid_list=openid_list)

        p = LgPageControl()
        e = LgErrorControl(error=kwargs['error']).appendto(p)
        p.append(openid_form)
        p.append(password_form)
        p.append(kwargs['new_account'])

        return p.gethtml()

        return """
<div class="lg_auth_form">
<span style="color:#ff0000;" class="lg_auth_error">{error}</span>
{openid}
{password}
{new_account}
</form>
</div>
        """.format(password=password_form,openid=openid_form, **kwargs)

    @cherrypy.expose
    def logout(self):
        config.auth.logout()
        redirect = config['logout_page']
        if redirect:
            raise cherrypy.HTTPRedirect(redirect)
        return "You have logged out."
        
    @cherrypy.expose
    def new_account_ok(self, username, redirect=''):
        redir_text = config.registrar.new_account_ok(username, redirect)
        if redirect:
            redir_link = """<p><a href="{0}">Click here to continue to your
original destination</a></p>""".format(redirect)

        return """<div class="lg_auth_form">{redirect}</div>""".format(redirect=redir_text)
    
    @cherrypy.expose
    def new_account(self, **kwargs):
        if config['site_registration'] is None:
            return """<div class="lg_auth_form">Registration is not available for this site.</div>"""

        redirect = kwargs.get('redirect', '')
    
        if cherrypy.request.method.upper() == 'POST':
            try:
                #check captcha
                keys = config['site_registration_recaptcha'] or {}
                pubkey = keys.get('public')
                if pubkey is not None:
                    privkey = keys.get('private')
                    from recaptcha.client import captcha
                    result = captcha.submit(
                        kwargs['recaptcha_challenge_field']
                        ,kwargs['recaptcha_response_field']
                        ,privkey
                        ,cherrypy.request.remote.ip
                        )
                    log('Recaptcha verification: ' + str(result.is_valid))
                    if not result.is_valid:
                        raise AuthError(result.error_code)

                uname = kwargs['username'].lower()
                uargs = { 'groups': [] }
                ok = True
                #Intermediate (not final) username existence check
                if ok:
                    error = config.auth.user_name_invalid(uname)
                    if error:
                        kwargs['error'] = error
                        ok = False
                if ok and config.auth.user_exists(uname):
                    kwargs['error'] = 'Username already taken'
                    ok = False
                if ok and 'password' in kwargs:
                    if kwargs['password'] != kwargs['password2']:
                        kwargs['error'] = 'Passwords did not match'
                        ok = False
                    error = passwords.check_complexity(kwargs['password'])
                    if error is not None:
                        kwargs['error'] = error
                        ok = False
                    else:
                        uargs['auth_password'] = {
                            'date': datetime.datetime.utcnow()
                            ,'pass': [ 'sha256', passwords.sha256(kwargs['password']) ]
                            }
                
                if ok and kwargs.get('openid', '') == 'stored':
                    uargs['auth_openid'] = [ cherrypy.session['openid_url'] ]
                
                if ok:
                    config.registrar.process_new_user(uname, uargs, kwargs, redirect)
                    raise cherrypy.HTTPRedirect(
                        url_add_parms(
                            'new_account_ok'
                            , { 
                                'username': uname
                                ,'redirect': redirect
                                }
                            )
                        )
            except AuthError as e:
                kwargs['error'] = e

        template_args = { 
            'openid': kwargs.get('openid', '') 
            ,'password_form': ''
            ,'error': kwargs.get('error', '')
            ,'username': kwargs.get('username', '')
            ,'redirect': redirect
            }
        if kwargs.get('openid') != 'stored':
            template_args['password_form'] = """
<tr><td>Password</td><td><input type="password" name="password" /></td></tr>
<tr><td>Password (again)</td><td><input type="password" name="password2" /></td></tr>
"""

        #Go through registration providers, and ask for fields
        reg_forms = []
        reg_forms.append(config.registrar.new_user_fields() or '')
        template_args['registration_forms'] = ''.join(reg_forms)
        
        #Captcha form
        template_args['captcha_form'] = ''
        keys = config['site_registration_recaptcha'] or {}
        pubkey = keys.get('public')
        if pubkey is not None:
            from recaptcha.client import captcha
            template_args['captcha_form'] = """<tr><td colspan="2">{captcha}</td></tr>""".format(captcha=captcha.displayhtml(pubkey))

        return """<div class="lg_auth_form lg_auth_new_account">
<span style="color:#ff0000;" class="lg_auth_error">{error}</span>
<form method="POST" action="new_account">
  <h1>New User Registration</h1>
  <input type="hidden" name="redirect" value="{redirect}" />
  <input type="hidden" name="openid" value="{openid}" />
  <table>
    <tr><td>Username</td><td><input type="text" name="username" value="{username}" /></td></tr>
    {password_form}
    {registration_forms}
    {captcha_form}
    <tr><td><input type="submit" value="Submit" /></td></tr>
  </table>
</form>
</div>""".format(**template_args)

    @cherrypy.expose
    def reg_response_link(self, **kwargs):
        return config.registrar.response_link(**kwargs)

    @cherrypy.expose
    def forgot_password(self, redirect):
        body = []
        body.append('<div class="lg_auth_form">')
        body.append('<p>If you have an e-mail registered with this site, enter it here to be e-mailed a password reset link:</p>')
        body.append('<form method="POST" action="forgot_password_email">')
        body.append('<input type="text" name="email" /><input type="submit" value="Submit" />')
        body.append('<input type="hidden" name="redirect" value="{redirect}"/>'.format(redirect=redirect))
        body.append('</form>')
        body.append('</div>')
        return ''.join(body)

    @cherrypy.expose
    def forgot_password_email(self, email, redirect):
        error = ''

        try:
            username = config.auth.get_user_from_email(email)
            if username is None:
                raise AuthError('Account matching e-mail not found.')
            user = config.auth.user_get_record(username)
            from uuid import uuid4
            code = uuid4().hex
            user['email_forgot_code'] = [ datetime.datetime.utcnow(), code ]

            from . import smail
            smail.send_mail(
                email
                , 'Forgot Password'
                , "You've indicated you forgot your password.  If that is true, click the following link to reset it.  Otherwise, you may disregard this e-mail.\r\n\r\n{link}".format(
                    link=url_add_parms(cherrypy.url('forgot_password_response'), { 'redirect': redirect, 'code': code, 'user': username })
                    )
                )
        except AuthError as e:
            import time
            time.sleep(0.1)
            error = str(e)

        if not error:
            error = "An e-mail has been sent to {email} with a link to reset your password.".format(email=email)
        raise cherrypy.HTTPRedirect(url_add_parms('login', { 'redirect': redirect, 'error': error }))

    @cherrypy.expose
    def forgot_password_response(self, user, code, redirect):
        error = 'Unknown error'
        try:
            u = config.auth.user_get_record(user)
            ucode = u.get('email_forgot_code')
            if ucode is None:
                raise AuthError('Unknown request')
            if (datetime.datetime.utcnow() - ucode[0]).days >= 1:
                raise AuthError('Unknown request')
            if code != ucode[1]:
                raise AuthError('Bad access code')

            del u['email_forgot_code']

            #OK!
            config.auth.login(user, admin=True)
            raise cherrypy.HTTPRedirect(url_add_parms('change_password', { 'redirect': redirect, 'error': 'Please enter a new password' }))

        except AuthError as e:
            error = str(e)

        raise cherrypy.HTTPRedirect(url_add_parms('login', { 'redirect': redirect, 'error': error }))


    @cherrypy.expose
    @groups('auth')
    def change_password(self, **kwargs):
        error = kwargs.get('error', '')
        redirect = kwargs.get('redirect', '')

        fresh_login = config.auth.login_is_admin()

        if not fresh_login:
            raise cherrypy.HTTPRedirect(
                url_add_parms(
                    'login'
                    , { 
                        'redirect': url_add_parms(cherrypy.url('change_password'), { 'redirect': redirect, 'error': 'Now enter your new password.' })
                        , 'error': 'Please confirm your login to modify your account.'
                        , 'admin': 'true'
                        }
                    )
                )

        if cherrypy.request.method.upper() == 'POST':
            try:
                if kwargs['newpass'] != kwargs['newpass2']:
                    raise AuthError('New passwords do not match')

                new_pass = kwargs['newpass']
                error = passwords.check_complexity(new_pass)
                if error is not None:
                    raise AuthError(error)

                config.auth.set_user_password(
                    cherrypy.user.id
                    , [ 'sha256', passwords.sha256(new_pass) ]
                    )
                if redirect:
                    raise cherrypy.HTTPRedirect(redirect)
                return "Password changed successfully."
            except AuthError as ae:
                error = str(ae)

        p = LgPageControl()
        err = LgErrorControl(error=error).appendto(p)
        form = GenericControl(
            '<form action="change_password" method="POST">{children}</form>'
            ).appendto(p)
        @Control.Kwarg('type', 'hidden', 'The type of the input')
        @Control.Kwarg('name', '', 'The name of the input')
        @Control.Kwarg('value', '', 'The default value')
        class InputControl(Control):
            template = '<input type="{type}" name="{name}"{value} />'
            def prerender(self, kwargs):
                if kwargs['value']:
                    kwargs['value'] = ' value="' + kwargs['value'] + '"'

        InputControl(name="redirect", value=redirect).appendto(form)
        par = GenericControl('<p>{children}</p>').appendto(form)

        par.append('Change Password: ')
        class TableControl(Control):
            template = '<table>{children}</table>'

        class RowControl(Control):
            template = '<tr>{children}</tr>'
            child_wrapper = [ '<td>', '</td>' ]

        table = TableControl().appendto(par)
        r1 = RowControl().append('New Password', InputControl(type='password', name='newpass')).appendto(table)
        r2 = RowControl().append('New Password (again)', InputControl(type='password', name='newpass2')).appendto(table)
        r3 = RowControl().append(InputControl(type='submit', value='Submit')).appendto(table)

        return p.gethtml()

        return """
<div class="lg_auth_form">
<span style="color:#ff0000;" class="lg_auth_error">{error}</span>
<form action="change_password" method="POST">
  <input type="hidden" name="redirect" value="{redirect}" />
  <p>
    Change Password:
    <table>
      <tr><td>New Password</td><td><input type="password" name="newpass" /></td></tr>
      <tr><td>New Password (again)</td><td><input type="password" name="newpass2" /></td></tr>
      <tr><td><input type="submit" value="Submit" /></td></tr>
    </table>
  </p>
</form>
</div>
        """.format(error=error, redirect=redirect)

    @cherrypy.expose
    @method_filter(methods=['POST'])
    def login_password(self, username, password, redirect=None, admin=False):
        #Case insensitive usernames
        username = username.lower()
        userId = config.auth.test_password(username, password)
        if userId is not None:
            config.auth.login(userId, admin=admin)
            self.login_redirect(redirect)
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
        try:
            username = config.auth.get_user_from_openid(url)
            if username is not None:
                config.auth.login(username, admin=kwargs.get('admin', False))
                self.login_redirect(redirect)
        except AuthError as ae:
            raise cherrypy.HTTPRedirect(
                url_add_parms('../login', { 'error': str(ae), 'redirect': redirect or '' })
                )

        #No known user has that openID... ask if they want to register,
        #if applicable.
        if config['site_registration'] is None:
            raise cherrypy.HTTPRedirect(
                url_add_parms('../login', { 'error': 'Unknown OpenID: ' + url, 'redirect': redirect or '' })
                )
        else:
            #We store the openid in session to prevent abusive services
            #registering a bunch of usernames with OpenID urls that do
            #not belong to them.
            cherrypy.session['openid_url'] = url
            raise cherrypy.HTTPRedirect(
                url_add_parms('../new_account', { 'error': 'Unknown OpenID.  If you would like to register an account with this OpenID, fill out the following form:', 'openid': 'stored', 'redirect': redirect or '' })
                )

