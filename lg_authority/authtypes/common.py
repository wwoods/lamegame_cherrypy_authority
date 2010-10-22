"""Common elements for all authtypes."""

import cherrypy
from .. import passwords

class AuthInterface(object):
    """The shared interface for authtypes.  Public functions that
    need to be overridden are specified first.
    """

    def get_user_record(self, username):
        """Returns the record for the given username (or None).  Should 
        be a dict that looks like the following: 
        { 'name': username, 'groups': [ 'groupid1', 'groupid2' ], 'info': {} }

        info contains e.g. 'email', 'firstname', 'lastname', etc.
        """
        raise NotImplementedError()

    def get_user_from_openid(self, openid_url):
        """Returns the username for the given openid_url, or None.
        """
        raise NotImplementedError()

    def get_user_password(self, username):
        """Returns a dict consisting of a "date" element that is the UTC time
        when the password was set, and a "pass" element that is the
        tuple/list (type, hashed_pass) for the given username.
        Returns None if the user specified does not have a password to
        authenticate through or does not exist.
        """
        raise NotImplementedError()

    def set_user_password(self, username, new_pass):
        """Updates the given user's password.  new_pass is a tuple
        (algorithm, hashed) that is the user's new password.
        
        Storage backends must keep track of the time when the password
        was set.
        """
        raise NotImplementedError()

    def _get_group_name(self, groupid):
        """Retrieves the name for the given groupid.  This is subclassed as
        _get_group_name because get_group_name automatically handles user-,
        any, and auth groups
        """
        raise NotImplementedError()

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

