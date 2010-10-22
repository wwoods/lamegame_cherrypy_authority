
from ...common import *

class SlateStorage(object): #PY3 , metaclass=cherrypy._AttributeDocstring):
    """The base class for slate storage types"""

    name = None
    name__doc = "The slate's name"

    def __init__(self, name, timeout):
        """Initializes storage for a slate.  Should clear data if expired,
        and update timestamp / timeout.

        timeout may be None for no expiration.

        It is recommended (if possible) to download and cache the "auth" key's
        value in the initial data request.
        """
        raise NotImplementedError()

    def set(self, key, value):
        """Sets the given key to the given value"""
        raise NotImplementedError()

    def get(self, key, default):
        """Gets the given key, or if it does not exist, returns default"""
        raise NotImplementedError()
        
    def pop(self, key, default):
        """Deletes and returns the value for the given key, or if it
        does not exist, returns default
        """
        raise NotImplementedError()

    def clear(self):
        """Erases all values.  Override for efficiency."""
        for k in self.keys():
            self.pop(k, None)

    def keys(self):
        """Returns an iterator or list of all keys."""
        raise NotImplementedError()

    def items(self):
        """Returns an iterator or list of all (key,value) pairs."""
        raise NotImplementedError()

    def values(self):
        """Returns an iterator or list of all values."""
        raise NotImplementedError()

    def expire(self):
        """Expire and/or delete the storage for a slate"""
        raise NotImplementedError()

    def update(self, d):
        """for k in d: self[k] = d[k].  Override to make more efficient."""
        for k,v in d.items():
            self.set(k, v)

    def setdefault(self, key, default):
        """Return the value for key.  If key is not set, set self[key] to default, and return default.  Override for efficiency."""
        result = self.get(key, missing)
        if result is missing:
            self.set(key, default)
            result = default
        return result

    @classmethod
    def setup(cls, config):
        """Set up slate storage medium according to passed config"""

    @classmethod
    def clean_up(cls):
        """Clean up expired sessions (timestamp + timeout < present)"""
        raise NotImplementedError()

    @classmethod
    def is_expired(cls, name):
        """Return True if the given slate is expired"""
        raise NotImplementedError()

