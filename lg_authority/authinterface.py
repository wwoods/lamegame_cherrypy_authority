import datetime

from .common import *
from . import passwords
from .slates import Slate

class UserObject:
    """An object representing the current logged in user.
    Served as cherrypy.user.
    """

    id = None
    id__doc = "The username of the current user"

    groups = []
    groups__doc = "List of groups to which the user belongs"

    slate = None
    slate__doc = "The user's slate for the current request"

    def __init__(self, session_dict):
        self.id = session_dict['__name__']
        self.groups = session_dict['groups']
        self.slate = Slate(
            cherrypy.serving.lg_authority['user_slate_section']
            ,self.id
            )

        #If they're logged in, they'd better be active.
        self.__slate__ = config.auth.user_get_record(self.id)

class AuthInterface(object):
    """The interface for auth-specific functions with the storage backend.
    """

    def user_name_invalid(self, username):
        """Return a human-readable error if username is invalid or
        has invalid characters.
        """
        if '"' in username or "'" in username:
            return "Name may not have quotes"
        if '<' in username or '>' in username:
            return "Name may not have > or <"
        if ' ' in username:
            return "Name may not have spaces"
        if '@' in username:
            return "Name may not contain the @ symbol"
        if '/' in username:
            return "Name may not contain the / symbol"
        return False

    def user_create(self, username, data, timeout=missing):
        """Inserts a user or raises an *Error"""
        kwargs = { 'timeout': None }
        if timeout is not missing:
            kwargs = { 'timeout': timeout, 'force_timeout': True }

        user = Slate('user', 'user-' + username)
        if not user.is_expired():
            raise AuthError('User already exists')

        user.update(data)
       
    def user_create_holder(self, username, data):
        """Inserts a placeholder for the given username.  Raises an AuthError
        if the username specified is already an existing user or placeholder
        user.
        """
        kwargs = { 'timeout': None }
        if config['site_registration_timeout'] != None:
            kwargs['timeout'] = config['site_registration_timeout'] * 60 * 24
            
        sname = Slate('user', 'user-' + username)
        if not sname.is_expired():
            raise AuthError('Username already taken')
            
        pname = Slate('user', 'userhold-' + username, **kwargs)
        if not pname.is_expired():
            raise AuthError('Username already taken')

        oname = Slate('user', 'userold-' + username)
        if not oname.is_expired():
            raise AuthError('Username already taken')
            
        #Make the holder
        pname.update(data)

    def user_exists(self, username):
        userrec = Slate('user', 'user-' + username)
        userhold = Slate('user', 'userhold-' + username)
        userold = Slate('user', 'userold-' + username)

        if not userrec.is_expired():
            return True
        if not userhold.is_expired():
            return True
        if not userold.is_expired():
            return True
        return False

    def user_get_holder(self, username):
        pname = 'userhold-' + username
        return Slate('user', pname)

    def user_promote_holder(self, holder):
        """Promotes the passed holder slate to a full user"""
        uname = 'user-' + holder.id[len('userhold-'):]
        uargs = {}
        for k,v in holder.items():
            uargs[k] = v

        user = Slate('user', uname)
        if not user.is_expired():
            raise AuthError('User already activated')

        user.update(uargs)
        holder.expire()

    def user_get_inactive(self, username):
        pname = 'userold-' + username
        return Slate('user', pname)

    def user_activate(self, username):
        pname = 'userold-' + username
        inact = Slate('user', pname)
        if inact.is_expired():
            raise AuthError('Cannot activate non-inactive user')

        items = inact.todict()
        nname = 'user-' + username
        s = Slate('user', nname)
        s.update(items)

        #Do this last to keep the user's data in case of unexpected error.
        inact.expire()

    def user_deactivate(self, username):
        oname = 'user-' + username
        act = Slate('user', oname)
        if act.is_expired():
            raise AuthError('Cannot deactive non-active user')

        items = act.todict()
        nname = 'userold-' + username
        s = Slate('user', nname)
        s.update(items)

        #Do this last to keep user's data in case of unexpected error
        act.expire()

    def user_get_record(self, username):
        """Returns the record for the given username (or None).
        """
        slate = Slate('user', 'user-' + username)
        return slate

    def get_user_from_email(self, email):
        """Returns the username for the given email, or None.
        """
        result = config.Slate.find_with('user', 'emails', email)
        if len(result) == 1 and result[0].id.startswith('user-'):
            return result[0].id[len('user-'):]
        elif len(result) == 1: #Inactive user
            raise AuthError('This e-mail is in use by an inactive user')
        elif len(result) == 0:
            return None
        else:
            raise AuthError("More than one user has this e-mail!")

    def get_user_from_openid(self, openid_url):
        """Returns the username for the given openid_url, or None.
        """
        result = config.Slate.find_with('user', 'auth_openid', openid_url)
        if len(result) == 0:
            return None
        elif len(result) == 1:
            if result[0].id.startswith('user-'):
                return result[0].id[len('user-'):]
            #Probably a disabled account or holder
            raise AuthError('This OpenID is in use by an inactive user')
        else:
            raise AuthError('This OpenID is in use')

    def get_user_password(self, username):
        """Returns a dict consisting of a "date" element that is the UTC time
        when the password was set, and a "pass" element that is the
        tuple/list (type, hashed_pass) for the given username.
        Returns None if the user specified does not have a password to
        authenticate through or does not exist.
        """
        user = Slate('user', 'user-' + username)
        if user.is_expired():
            return None
        return user.get('auth_password', None)

    def set_user_password(self, username, new_pass):
        """Updates the given user's password.  new_pass is a tuple
        (algorithm, hashed) that is the user's new password.
        """
        user = Slate('user', 'user-' + username)
        if user.is_expired():
            raise ValueError('User not found')
        user['auth_password'] = { 'date': datetime.datetime.utcnow(), 'pass': new_pass }

        #Clear any admin login flag
        cherrypy.session.pop('authtime_admin')

    def _get_group_name(self, groupid):
        """Retrieves the name for the given groupid.  This is subclassed as
        _get_group_name because get_group_name automatically handles user-,
        any, and auth groups
        """
        group = Slate('user', 'group-' + groupid)
        if not group.is_expired():
            return group['name']
        return 'Unnamed ({0})'.format(groupid)

    def group_create(self, groupid, data, timeout=missing):
        """Insert the specified group, or raise an *Error"""
        kwargs = { 'timeout': None }
        if timeout is not missing:
            kwargs = { 'timeout': timeout, 'force_timeout': True }

        sname = Slate('user', 'group-' + groupid, **kwargs)
        if not sname.is_expired():
            raise AuthError('Group already exists')

        sname.update(data)

    def login(self, username, admin=False):
        """Logs in the specified username.  Returns the user record."""
        record = self.user_get_record(username)
        d = record.todict()
        d['__name__'] = username
        cherrypy.session['auth'] = d
        cherrypy.session['authtime'] = datetime.datetime.utcnow()
        if admin:
            cherrypy.session['authtime_admin'] = datetime.datetime.utcnow()

        self.serve_user_from_dict(d)
        return record

    def login_time_elapsed(self):
        """Gets the # of seconds elapsed since the last login."""
        t = datetime.datetime.utcnow() - cherrypy.session['authtime']
        return t.days * 24 * 60 * 60 + t.seconds

    def login_is_admin(self):
        """Returns True if the current login is allowed to make administrative
        changes to the account, or False otherwise.
        """
        authtime_admin = cherrypy.session.get('authtime_admin')
        if authtime_admin is None:
            return False
        t = datetime.datetime.utcnow() - authtime_admin
        if t.days * 24 * 60 * 60 + t.seconds < config['site_admin_login_window']:
            return True
        return False

    def serve_user_from_dict(self, d):
        """Sets cherrypy.serving.user based on the passed auth dict.
        d may be None.
        """
        if d is not None:
            cherrypy.serving.user = UserObject(d)
        else:
            cherrypy.serving.user = None

    def logout(self):
        """Log out the current logged in user."""
        if hasattr(cherrypy.session, 'expire'):
            cherrypy.session.expire()
        else:
            cherrypy.lib.sessions.expire()

    def old_password(self, username):
        renew = config['site_password_renewal']
        if renew is None:
            return
        passw = self.get_user_password(username)
        if passw is None:
            #No password, they don't need to renew probably!
            return False
        if (datetime.datetime.utcnow() - passw['date']).days >= renew:
            return True
        return False

    def test_password(self, username, password):
        "Returns username for OK, None for failed auth"
        if '@' in username:
            #Map e-mail to user
            username = self.get_user_from_email(username)
            if username is None:
                return None
        expected = self.get_user_password(username)
        if expected is None:
            return None

        if passwords.verify(password, expected['pass']):
            return username
        return None

    def get_group_name(self, groupid):
        """Returns the common name for the given groupid.
        groupid may be the special identifiers 'any', 'auth', or 'user-'
        as well.
        """

        if groupid == 'any':
            return 'Everyone'
        elif groupid == 'auth':
            return 'Logged In Users'
        elif groupid.startswith('user-'):
            return 'User - ' + groupid[5:]
        return self._get_group_name(groupid)

