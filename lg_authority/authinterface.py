import datetime
import re
import uuid

from .common import *
from . import passwords
from .slates import Slate
from .authtoken import AuthToken

class UserHolder:
    """Though holders are saved internally as username slates with a special
    property, we extract that property into this object for presentation and
    encapsulation.
    """

    def __init__(self, slate):
        if slate is None or slate.is_expired() or slate.get('holder') is None:
            raise ValueError("slate must be valid holder")
        self._slate = slate
        self.data = slate['holder']

    def promote(self):
        """Turn the holder into a real user.  Returns the new user ID
        """
        return config.auth._promote_holder(self)

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
        self.dict = Slate('user', self.id)
        self.session = Slate('user_session', self.id)

    def addToGroup(self, group):
        """Adds this user to the specified group, permanently.
        """
        self.dict['groups'] += [ group ]

        # Update logged in data if necessary
        oldAuth = cherrypy.serving.sessionActual.get('auth')
        if oldAuth is not None:
            oldAuth['groups'] += [ group ]
            cherrypy.serving.sessionActual['auth'] = oldAuth

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

        Else returns None (name is ok)
        """
        if len(username) > 40:
            return "Name is too long"
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
        if not re.match(r'^[a-zA-Z0-9_\.]+$', username):
            return "Name must only contain latin characters, underscores, or periods"
        return None

    def user_create(self, userName, data):
        """Inserts a user or raises an *Error
        
        Returns the user ID for the new user.
        """
        kwargs = { 'timeout': None }

        usernameError = None
        # Bypass name checking if we're using e-mail
        if userName not in data.get('emails', []):
            usernameError = self.user_name_invalid(userName)
        if usernameError is not None:
            raise AuthError(usernameError)

        userNameSlate = Slate('username', userName, timeout=kwargs['timeout'])
        if not userNameSlate.is_expired():
            raise AuthError("User already exists")

        user = Slate('user', None, timeout=kwargs['timeout'])
        if not user.is_expired():
            raise AuthError("User creation failed")

        dataNew = data.copy()
        dataNew['name'] = userName
        user.update(dataNew)
        userNameSlate['userId'] = user.id
        return user.id
       
    def user_create_holder(self, userName, data, timeout=None):
        """Inserts a placeholder for the given username.  Raises an AuthError
        if the username specified is already an existing user or placeholder
        user.

        data is any authentication data to associate with the user.
        timeout - The timeout interval for this holder, in seconds
        """
        pname = Slate('username', userName, timeout=timeout)
        if not pname.is_expired():
            raise AuthError('Username already taken')
            
        #Make the holder
        newData = { 'holder': data }
        pname.update(newData)

    def user_delete(self, userId):
        user = self.get_user_from_id(userId)
        if user is not None and user.get('inactive', False):
            username = user.get('name')
            if username is not None:
                uname = Slate('username', username)
                if uname.get('userId') == userId:
                    uname.expire()
            user.expire()
        elif user is not None:
            raise AuthError("Cannot delete active user; deactivation is " \
                + "required to " \
                + "remind administrators that deleting a record can result " \
                + "in data corruption.")
        else:
            raise AuthError("User does not exist")

    def user_exists(self, username):
        if not Slate('username', username).is_expired():
            return True
        return False

    def user_activate(self, userId):
        user = self.get_user_from_id(userId)
        if user.is_expired() or not user.get('inactive', False):
            raise AuthError('Cannot activate non-inactive user')

        del user['inactive']

    def user_deactivate(self, userId):
        user = self.get_user_from_id(userId)
        if user.is_expired():
            raise AuthError("Invalid user ID")

        user['inactive'] = datetime.datetime.utcnow()

    def get_user_from_id(self, userId):
        """Returns the record for the given user Id (or None).
        """
        slate = Slate('user', userId)
        if slate.is_expired():
            slate = None
        return slate

    def get_user_from_name(self, username):
        """Returns the record for the given username (or None if the user
        does not exist).
        """
        slate = Slate('username', username)
        if not slate.is_expired():
            userId = slate['userId']
            if userId is None:
                # This record is probably a holder
                return None
            slate = Slate('user', slate['userId'])
            if slate.is_expired():
                return None
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
            return result
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

    def get_user_from_token(self, authToken):
        """Returns the slate for the use rwith the given authToken, or None.
        """
        if AuthToken.isExpired(authToken):
            raise AuthError("This authToken is no longer valid")
        result = config.Slate.find_with('user', 'auth_token', authToken)
        if len(result) == 0:
            return None
        elif len(result) > 1:
            raise AuthError('This authToken belongs to multiple users')
        else:
            result = result[0]
            if result.get('inactive', False):
                raise AuthError("This authToken belongs to inactive user")
            return result

    def get_user_holder(self, username):
        """Returns the given username record, only if that record has the
        'holder' property set to True.  Otherwise returns None.
        """
        result = Slate('username', username)
        if result.is_expired() or not result.get('holder', False):
            return None
        return UserHolder(result)

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

    def set_user_password(self, userid, new_pass):
        """Updates the given user's password.  new_pass is a tuple
        (algorithm, hashed) that is the user's new password.
        """
        user = self.get_user_from_id(userid)
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
        # We no longer do this since it can cause weird errors, and it makes
        # sense that the application needs to know which data is attached
        # to a browser session and which to a user.  moved to 
        # cherrypy.user.session
        #user_session = Slate('user_session', userId, timeout=None)
        #for k,v in cherrypy.serving.sessionActual.items():
        #    if k == 'auth':
        #        # Never port over auth data
        #        continue
        #    if k in user_session:
        #        raise Exception("Session migration was not smooth: " + k)
        #    user_session[k] = v
        #    del cherrypy.serving.sessionActual[k]
        #cherrypy.serving.session = user_session

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
        else:
            # Get the user record
            user = self.get_user_from_name(username)
            
        if user is None or user.get('inactive', False):
            return None
            
        expected = self.get_user_password(user)
        if expected is None:
            return None

        if passwords.verify(password, expected['pass']):
            return user.id
        return None

    def token_create(self, userId):
        """Checks if a token can be created for the given user.  Raises a
        TokenExistedError with the old token if the user already had a token
        that is good for more than 90 days)
        """
        user = self.get_user_from_id(userId)
        authTokens = user.get('auth_token', [])
        tokensToRemove = []
        for token in authTokens:
            if AuthToken.isExpired(token):
                tokensToRemove.append(token)
            elif AuthToken.isTooRecentForNew(token):
                raise TokenExistedError(token)
        for t in tokensToRemove:
            authTokens.remove(t)
        newToken = AuthToken.create(user.id, user['name'], 365*2)
        authTokens.append(newToken)
        user['auth_token'] = authTokens
        return newToken

    def token_delete(self, userId, tokenDelete):
        """Deletes the specified token from the user's account"""
        user = self.get_user_from_id(userId)
        authTokens = user.get('auth_token', [])
        authTokens.remove(tokenDelete)
        user['auth_token'] = authTokens

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

    def _promote_holder(self, holder):
        """Promotes the passed holder slate to a full user.  Assumes that
        holder is a valid slate.

        Returns the created user ID.
        """
        nameSlate = holder._slate
        if not nameSlate.get('holder', False):
            raise AuthError('User already activated')

        uargs = {}
        for k,v in holder.data.items():
            uargs[k] = v

        # Inform the user of its name
        uargs['name'] = nameSlate.id

        user = Slate('user', None, timeout=None)
        if not user.is_expired():
            raise AuthError('User creation error')

        nameSlate.set_timeout(None)
        user.update(uargs)
        uid = user.id
        nameSlate['userId'] = uid
        del nameSlate['holder']

        return uid

