"""Non-persistent user store that is configured entirely through
CherryPy's configuration methods.
"""

import datetime
from .common import AuthInterface

class UserListInterface(AuthInterface):
    def __init__(self, options):
        self.options = options
        self.users = options['users']
        self.groups = options['groups']

    def get_user_record(self, username):
        user = self.users.get(username)
        if user is not None:
            return {
                'name': username
                ,'groups': user.get('groups', [])
                }
        return None

    def get_user_password(self, username):
        user = self.users.get(username)
        p = None
        if user is not None:
            p = user.get('auth', {}).get('password', None)
        return p

    def set_user_password(self, username, password):
        user = self.users.get(username)
        if user is None:
            raise ValueError("User not found?")
        user.setdefault('auth', {})['password'] = { 'date': datetime.datetime.utcnow(), 'pass': password }

    def _get_group_name(self, groupid):
        record = self.groups.get(groupid, {})
        return record.get('name', groupid)

def setup(options):
    return UserListInterface(options)

