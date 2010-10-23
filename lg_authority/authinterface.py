import datetime

from .common import *
from . import passwords
from .slates import Slate

class AuthInterface(object):
    """The interface for auth-specific functions with the storage backend.
    """

    def user_create(self, username, data, timeout=missing):
        """Inserts a user or raises an *Error"""
        kwargs = { 'timeout': None }
        if timeout is not missing:
            kwargs = { 'timeout': timeout, 'force_timeout': True }

        sname = config['site_user_prefix'] + username
        if not Slate.is_expired(sname):
            raise Exception('User already exists')

        user = Slate(sname, **kwargs)
        user.update(data)

    def get_user_record(self, username):
        """Returns the record for the given username (or None).  Should 
        be a dict that looks like the following: 
        { 'name': username, 'groups': [ 'groupid1', 'groupid2' ], 'info': {} }

        info contains e.g. 'email', 'firstname', 'lastname', etc.
        """
        slate = Slate.lookup(config['site_user_prefix'] + username)
        if slate is None:
            return None
        return {
            'name': username
            ,'groups': slate['groups']
            }

    def get_user_from_openid(self, openid_url):
        """Returns the username for the given openid_url, or None.
        """
        result = config.storage_class.find_slates_with('auth_openid', openid_url)
        if len(result) == 0:
            return None
        elif len(result) == 1:
            return result[0][len(config['site_user_prefix']):]
        else:
            raise ValueError('More than one user has this OpenID')

    def get_user_password(self, username):
        """Returns a dict consisting of a "date" element that is the UTC time
        when the password was set, and a "pass" element that is the
        tuple/list (type, hashed_pass) for the given username.
        Returns None if the user specified does not have a password to
        authenticate through or does not exist.
        """
        user = Slate.lookup(config['site_user_prefix'] + username)
        return user and user.get('auth_password', None)

    def set_user_password(self, username, new_pass):
        """Updates the given user's password.  new_pass is a tuple
        (algorithm, hashed) that is the user's new password.
        """
        user = Slate.lookup(config['site_user_prefix'] + username)
        if user is None:
            raise ValueError('User not found')
        user['auth_password'] = { 'date': datetime.datetime.utcnow(), 'pass': new_pass }

    def _get_group_name(self, groupid):
        """Retrieves the name for the given groupid.  This is subclassed as
        _get_group_name because get_group_name automatically handles user-,
        any, and auth groups
        """
        group = Slate.lookup(config['site_group_prefix'] + groupid)
        if group is not None:
            return group['name']
        return 'Unnamed ({0})'.format(groupid)

    def group_create(self, groupid, data, timeout=missing):
        """Insert the specified group, or raise an *Error"""
        kwargs = { 'timeout': None }
        if timeout is not missing:
            kwargs = { 'timeout': timeout, 'force_timeout': True }

        sname = config['site_group_prefix'] + groupid
        if not Slate.is_expired(sname):
            raise Exception('Group already exists')

        group = Slate(sname, **kwargs)
        group.update(data)

    def login(self, username):
        """Logs in the specified username.  Returns the user record."""
        record = self.get_user_record(username)
        cherrypy.session['auth'] = record
        return record

    def logout(self):
        """Log out the current logged in user."""
        if hasattr(cherrypy.session, 'expire'):
            cherrypy.session.expire()
        else:
            cherrypy.lib.sessions.expire()

    def test_password(self, username, password):
        "Returns True for OK, False for failed auth"
        expected = self.get_user_password(username)
        if expected is None:
            return False

        if passwords.verify(password, expected['pass']):
            return True
        return False

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

