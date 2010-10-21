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
        { 'name': username, 'groups': [ 'groupid1', 'groupid2' ] }
        """
        raise NotImplementedError()

    def get_user_password(self, username):
        """Returns a tuple/list (type, hashed_pass) for the given username.
        Returns None if the user specified does not have a password to
        authenticate through or does not exist.
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

        if passwords.verify(password, expected):
            return True
        return False

