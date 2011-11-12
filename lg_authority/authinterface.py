import datetime
import uuid

from .common import *
from . import passwords
from .slates import Slate

class UserObject:
    """An object representing the current logged in user.
    Served as cherrypy.user.
    """

    id = None
    id__doc = "The id of the current user"

    groups = []
    groups__doc = "List of groups to which the user belongs"

    name = None
    name__doc = "The username of the current user"

    SESSION_USER_NOT_FROM_SLATE = '__name__not_from_db'
    SESSION_USER_NOT_FROM_SLATE__doc = """If set in session, indicates that 
        the user was logged in externally
        """

    def __init__(self, session_dict):
        self.id = session_dict['__id__']
        self.name = session_dict['__name__']
        self.groups = session_dict['groups']

    def isOldPassword(self):
        """Returns True if our password is old and should be changed."""
        renew = config['site_password_renewal']
        if renew is None:
            return False
        user = config.auth.get_user_from_id(self.id)
        passw = config.auth.get_user_password(user)
        if passw is None:
            #No password, they don't need to renew probably!
            return False
        if (datetime.datetime.utcnow() - passw['date']).days >= renew:
            return True
        return False


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

    def user_create(self, userName, data):
        """Inserts a user or raises an *Error
        
        Returns the user ID for the new user.
        """
        kwargs = { 'timeout': None }

        userNameSlate = Slate('username', userName, timeout=kwargs['timeout'])
        if not userNameSlate.is_expired():
            raise AuthError("User already exists")

        user = Slate('user', uuid.uuid4().hex
            , timeout=kwargs['timeout'])
        if not user.is_expired():
            raise AuthError("User creation failed")

        dataNew = data.copy()
        dataNew['name'] = userName
        user.update(dataNew)
        userNameSlate['userId'] = user.id
        return user.id
       
    def user_create_holder(self, userName, data):
        """Inserts a placeholder for the given username.  Raises an AuthError
        if the username specified is already an existing user or placeholder
        user.
        """
        kwargs = { 'timeout': None }
        if config['site_registration_timeout'] != None:
            kwargs['timeout'] = config['site_registration_timeout'] * 60 * 24
            
        pname = Slate('username', username, **kwargs)
        if not pname.is_expired():
            raise AuthError('Username already taken')
            
        #Make the holder
        pname.update(data)

    def user_exists(self, username):
        if self.get_user_from_name(username) is not None:
            return True
        return False

    def user_get_holder(self, username):
        pname = 'userhold-' + username
        return Slate('user', pname)

    def user_promote_holder(self, holder):
        """Promotes the passed holder slate to a full user"""
        uid = holder.id
        uargs = {}
        for k,v in holder.items():
            uargs[k] = v

        user = Slate('user', uid)
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
        nname = username
        s = Slate('user', nname)
        s.update(items)

        #Do this last to keep the user's data in case of unexpected error.
        inact.expire()

    def user_deactivate(self, username):
        oname = username
        act = Slate('user', oname)
        if act.is_expired():
            raise AuthError('Cannot deactive non-active user')

        items = act.todict()
        nname = 'userold-' + username
        s = Slate('user', nname)
        s.update(items)

        #Do this last to keep user's data in case of unexpected error
        act.expire()

    def get_user_from_id(self, userId):
        """Returns the record for the given user Id (or None).
        """
        slate = Slate('user', userId)
        if slate.is_expired():
            slate = None
        return slate

    def get_user_from_name(self, username):
        """Returns the record for the given username (or None).
        """
        slate = Slate('username', username)
        if not slate.is_expired():
            slate = Slate('user', slate['userId'])
        else:
            slate = None
        return slate

    def get_user_from_email(self, email):
        """Returns the user ID for the given email, or None.
        """
        result = config.Slate.find_with('user', 'emails', email)
        if len(result) == 1:
            result = result[0]
            if result.get('inactive', False):
                raise AuthError('This e-mail is in use by an inactive user')
            return result.id
        elif len(result) > 1:
            raise AuthError("More than one user has this e-mail!")
        else:
            return None

    def get_user_from_openid(self, openid_url):
        """Returns the username for the given openid_url, or None.
        """
        result = config.Slate.find_with('user', 'auth_openid', openid_url)
        if len(result) == 0:
            return None
        elif len(result) == 1:
            result = result[0]
            if result.get('inactive', False):
                raise AuthError('This OpenID is in use by an inactive user')
            return result.id
        else:
            raise AuthError('This OpenID is in use by multiple users')

    def get_user_password(self, userSlate):
        """Returns a dict consisting of a "date" element that is the UTC time
        when the password was set, and a "pass" element that is the
        tuple/list (type, hashed_pass) for the given username.
        Returns None if the user specified does not have a password to
        authenticate through or does not exist.
        """
        if userSlate.is_expired():
            return None
        return userSlate.get('auth_password', None)

    def set_user_password(self, username, new_pass):
        """Updates the given user's password.  new_pass is a tuple
        (algorithm, hashed) that is the user's new password.
        """
        user = self.get_user_from_name(username)
        if user.is_expired():
            raise ValueError('User not found')
        user['auth_password'] = { 'date': datetime.datetime.utcnow(), 'pass': new_pass }

        #Clear any admin login flag
        cherrypy.serving.session.pop('authtime_admin')

    def _get_group_name(self, groupid):
        """Retrieves the name for the given groupid.  This is subclassed as
        _get_group_name because get_group_name automatically handles user-,
        any, and auth groups
        """
        group = Slate('group', groupid)
        if not group.is_expired():
            return group['name']
        return 'Unnamed ({0})'.format(groupid)

    def group_create(self, groupid, data, timeout=missing):
        """Insert the specified group, or raise an *Error"""
        kwargs = { 'timeout': None }
        if timeout is not missing:
            kwargs = { 'timeout': timeout }

        sname = Slate('group', groupid, **kwargs)
        if not sname.is_expired():
            raise AuthError('Group already exists')

        sname.update(data)

    def login(self, userId, userName=None, admin=False, groups=[], external_auth=False):
        """Logs in the specified user id / name.  Returns the user record.
        
        @param external_auth Set to True if this user doesn't come from local
            authentication.  Necessary to set or else we'll try to get their
            slate.
            
        @param groups Set to an array of groups to additionally give the user.
            Only valid if external_auth is set.
            
        """
        
        if not external_auth:
            if userName is not None:
                raise ValueError("Do not specify userName for internal auth")
            print("got user ID " + userId)
            record = self.get_user_from_id(userId)
            if record is None:
                raise ValueError("Invalid user ID")
            d = record.todict()
            d['__name__'] = record['name']
        else:
            if userName is None:
                raise ValueError("userName must be specified for external auth")
            record = {
                'groups': groups
                ,'__name__': userName
                ,UserObject.SESSION_USER_NOT_FROM_SLATE: True
                }
            d = record
        d['__id__'] = userId
        d['authtime'] = datetime.datetime.utcnow()
        if admin:
            d['authtime_admin'] = datetime.datetime.utcnow()

        #Guard against session fixation - see regen_id docstring
        cherrypy.serving.sessionActual.regen_id()

        #Port over session variables
        user_session = Slate('user_session', userId, timeout=None)
        for k,v in cherrypy.serving.sessionActual.items():
            if k in user_session:
                raise Exception("Session migration was not smooth: " + k)
            user_session[k] = v
            del cherrypy.serving.sessionActual[k]
        cherrypy.serving.session = user_session

        #Set our auth entry...
        cherrypy.serving.sessionActual['auth'] = d

        self.serve_user_from_dict(d)
        return record

    def login_time_elapsed(self):
        """Gets the # of seconds elapsed since the last login."""
        t = datetime.datetime.utcnow() \
          - cherrypy.serving.sessionActual['auth']['authtime']
        return t.days * 24 * 60 * 60 + t.seconds

    def login_is_admin(self):
        """Returns True if the current login is allowed to make administrative
        changes to the account, or False otherwise.
        """
        authtime_admin = cherrypy.serving.sessionActual['auth'].get('authtime_admin')
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
        if hasattr(cherrypy.serving, 'sessionActual'):
            cherrypy.serving.sessionActual.expire()
        else:
            cherrypy.lib.sessions.expire()

    def test_password(self, username, password):
        "Returns user id for OK, None for failed auth"
        if '@' in username:
            #Map e-mail to user
            user = self.get_user_from_email(username)
            if user is None:
                return None
        else:
            # Get the user record
            user = self.get_user_from_name(username)
        expected = self.get_user_password(user)
        if expected is None:
            return None

        if passwords.verify(password, expected['pass']):
            return user.id
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
            user = self.get_user_from_id(groupid[5:])
            return 'User - ' + user.get('name', '(error)')
        return self._get_group_name(groupid)

