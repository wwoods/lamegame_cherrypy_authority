import datetime

from .common import *
from . import passwords
from .slates import Slate

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
        return False

    def user_create(self, username, data, timeout=missing):
        """Inserts a user or raises an *Error"""
        kwargs = { 'timeout': None }
        if timeout is not missing:
            kwargs = { 'timeout': timeout, 'force_timeout': True }

        sname = 'user-' + username
        if not Slate.is_expired('user', sname):
            raise AuthError('User already exists')

        user = Slate('user', sname, **kwargs)
        user.update(data)
       
    def user_create_holder(self, username, data):
        """Inserts a placeholder for the given username.  Raises an AuthError
        if the username specified is already an existing user or placeholder
        user.
        """
        kwargs = { 'timeout': None }
        if config['site_registration_timeout'] != None:
            kwargs['timeout'] = config['site_registration_timeout'] * 60 * 24
            
        sname = 'user-' + username
        if not Slate.is_expired('user', sname):
            raise AuthError('Username already taken')
            
        pname = 'userhold-' + username
        if not Slate.is_expired('user', pname):
            raise AuthError('Username already taken')
            
        pslate = Slate('user', pname, **kwargs)
        pslate.update(data)

    def user_exists(self, username):
        userrec = 'user-' + username
        userhold = 'userhold-' + username

        if not Slate.is_expired('user', userrec):
            return True
        if not Slate.is_expired('user', userhold):
            return True
        return False

    def user_get_holder(self, username):
        pname = 'userhold-' + username
        return Slate.lookup('user', pname)

    def user_promote_holder(self, holder):
        """Promotes the passed holder slate to a full user"""
        uname = 'user-' + holder.name[len('userhold-'):]
        uargs = {}
        for k,v in holder.items():
            uargs[k] = v

        if not Slate.is_expired('user', uname):
            raise AuthError('User already activated')

        user = Slate('user', uname)
        user.update(uargs)
        holder.expire()

    def user_get_inactive(self, username):
        pname = 'userold-' + username
        return Slate.lookup('user', pname)

    def user_activate(self, username):
        pname = 'userold-' + username
        inact = Slate.lookup('user', pname)
        if inact is None:
            raise AuthError('Cannot activate non-inactive user')

        items = inact.todict()
        nname = 'user-' + username
        s = Slate('user', nname)
        s.update(items)

        #Do this last to keep the user's data in case of unexpected error.
        inact.expire()

    def user_deactivate(self, username):
        oname = 'user-' + username
        act = Slate.lookup('user', oname)
        if act is None:
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
        slate = Slate.lookup('user', 'user-' + username)
        return slate

    def get_user_from_email(self, email):
        """Returns the username for the given email, or None.
        """
        result = config.storage_class.find_slates_with('user', 'emails', email)
        if len(result) == 1 and result[0].startswith('user-'):
            return result[0][len('user-'):]
        elif len(result) == 1: #Inactive user
            return None
        elif len(result) == 0:
            return None
        else:
            raise AuthError("More than one user has this e-mail!")

    def get_user_from_openid(self, openid_url):
        """Returns the username for the given openid_url, or None.
        """
        result = config.storage_class.find_slates_with('user', 'auth_openid', openid_url)
        if len(result) == 0:
            return None
        elif len(result) == 1:
            if result[0].startswith('user-'):
                return result[0][len('user-'):]
            #Probably an inactive account.
            return None
        else:
            raise AuthError('More than one user has this OpenID')

    def get_user_password(self, username):
        """Returns a dict consisting of a "date" element that is the UTC time
        when the password was set, and a "pass" element that is the
        tuple/list (type, hashed_pass) for the given username.
        Returns None if the user specified does not have a password to
        authenticate through or does not exist.
        """
        user = Slate.lookup('user', 'user-' + username)
        return user and user.get('auth_password', None)

    def set_user_password(self, username, new_pass):
        """Updates the given user's password.  new_pass is a tuple
        (algorithm, hashed) that is the user's new password.
        """
        user = Slate.lookup('user', 'user-' + username)
        if user is None:
            raise ValueError('User not found')
        user['auth_password'] = { 'date': datetime.datetime.utcnow(), 'pass': new_pass }

    def _get_group_name(self, groupid):
        """Retrieves the name for the given groupid.  This is subclassed as
        _get_group_name because get_group_name automatically handles user-,
        any, and auth groups
        """
        group = Slate.lookup('user', 'group-' + groupid)
        if group is not None:
            return group['name']
        return 'Unnamed ({0})'.format(groupid)

    def group_create(self, groupid, data, timeout=missing):
        """Insert the specified group, or raise an *Error"""
        kwargs = { 'timeout': None }
        if timeout is not missing:
            kwargs = { 'timeout': timeout, 'force_timeout': True }

        sname = 'group-' + groupid
        if not Slate.is_expired('user', sname):
            raise AuthError('Group already exists')

        group = Slate('user', sname, **kwargs)
        group.update(data)

    def login(self, username):
        """Logs in the specified username.  Returns the user record."""
        record = self.user_get_record(username)
        d = record.todict()
        d['__name__'] = username
        cherrypy.session['auth'] = d

        self.serve_user_from_dict(d)
        return record

    def serve_user_from_dict(self, d):
        """Sets cherrypy.serving.user based on the passed auth dict.
        d may be None.
        """
        user = d and ConfigDict(d)
        cherrypy.serving.user = user
        if user is not None:
            user.name = user['__name__'] #Convenience
            user.groups = user['groups'] #Convenience
            user.slate = Slate(
                cherrypy.serving.lg_authority['user_slate_section'], user.name
                )

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

