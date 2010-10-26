
from ...common import *

class SlateStorage(object): #PY3 , metaclass=cherrypy._AttributeDocstring):
    """The base class for slate storage types.  These should only use the
    most basic library available for the given storage type.
    """

    name = None
    name__doc = "The slate's name"

    def __init__(self, section, name, timeout, force_timeout):
        """Initializes storage for a slate.  Should clear data if expired,
        and update timestamp / timeout.

        timeout may be None for no expiration.

        If force_timeout is set, then the slate's timeout MUST be set to the
        specified timeout, even if the slate already exists.

        It is recommended (if possible) to download and cache the "auth" key's
        value in the initial data request.
        """
        raise NotImplementedError()

    def set(self, key, value):
        """Sets the given key to the given value.  If value is a list of 
        unique strings,
        it is recommended that drivers keep the array indexable rather
        than directly pickling it.  This is used by the authentication system,
        specifically for groups and openID.
        """
        raise NotImplementedError()

    def get(self, key, default):
        """Gets the given key, or if it does not exist, returns default"""
        raise NotImplementedError()

    @classmethod
    def find_slates_with(cls, section, key, value):
        """Return a list of slate names having value in the array keyed by
        key.  key must be in site_storage_sections' index_lists parameter
        for the given section.
        """
        raise NotImplementedError()

    @classmethod
    def find_slates_between(cls, section, start, end, limit=None, skip=None):
        """Return a list of slate names between start and end, optionally
        limiting the number of results and/or skipping the first X results.
        """
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

    def items(self):
        """Returns an iterator or list of all (key,value) pairs."""
        raise NotImplementedError()

    def expire(self):
        """Expire and/or delete the storage for a slate"""
        raise NotImplementedError()

    def keys(self):
        """Returns an iterator or list of all keys."""
        return [ d[0] for d in self.items() ]

    def values(self):
        """Returns an iterator or list of all values."""
        return [ d[1] for d in self.items() ]

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
        """Clean up expired sessions (expired < present).  It is recommended
        that drivers keep track of sections that have been used and clean
        those, ignoring unused sections.
        """
        raise NotImplementedError()

    @classmethod
    def is_expired(cls, section, name):
        """Return True if the given slate is expired or does not exist"""
        raise NotImplementedError()

    @classmethod
    def get_section_config(cls, section):
        return config.get('site_storage_sections_' + section, {})

