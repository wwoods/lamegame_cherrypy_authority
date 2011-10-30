
from ...common import *

class SlateStorage(object): #PY3 , metaclass=cherrypy._AttributeDocstring):
    """The base class for slate storage types.  These should only use the
    most basic library available for the given storage type.
    """

    name = None
    name__doc = "The slate's name"

    def __init__(self, section, id, timeout):
        """Initializes storage for a slate.  Shouldn't do any network activity.

        If id is unspecified (None), this storage should note that and 
        assign a new, unique identifier on any write operation.
        
        If timeout is specified, then the slate's timeout is to be set to the
        specified timeout on any write, even if the slate already exists.  If
        timeout is unspecified, its value will be a dict.  Use 
        isinstance(timeout, dict) to see if timeout is specified.
        """
        raise NotImplementedError()

    def touch(self):
        """Touch the Slate; that is, update its expiration time but do not
        write any other data.
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

    def is_expired(self):
        """Return True if this Slate is expired, or False otherwise."""
        raise NotImplementedError()

    def time_to_expire(self):
        """Return the cached (as of first data access) number of seconds
        before this Slate will expire.

        Return 0 if this slate is already expired.
        Return None if it will never expire.  
        
        The minimum numeric value returned is zero.
        """
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

    def is_expired(self):
        """Return True if this given slate is expired or does not exist"""
        raise NotImplementedError()

    def get_section_config(self):
        """Instance method to get the section config"""
        return config.get('site_storage_sections_' + self.section, {})

    @classmethod
    def _get_section_config(cls, section):
        """Class method to get the section config"""
        return config.get('site_storage_sections_' + section, {})

    @classmethod
    def destroySectionBeCarefulWhenYouCallThis(cls, section):
        """DO NOT call unless you know what you are doing or are a test
        environment.  Deletes all slates under the given section.
        """
        raise NotImplementedError()

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
    def count_with(cls, section, key, value):
        """Return the number of slate names having value in the array keyed
        by key.  key must be in site_storage_sections_{section}'s index_lists
        parameter.
        """
        return len(cls.find_with(section, key, value))

    @classmethod
    def find_with(cls, section, key, value):
        """Return a list of slates having value in the array keyed by
        key.  key must be in site_storage_sections_{section}' index_lists 
        parameter for the given section.
        """
        raise NotImplementedError()

    @classmethod
    def count_between(cls, section, start, end):
        """Returns the number of slates whose names fall (inclusively)
        between start and end in the given section.
        """
        return len(cls.find_between(section, start, end))

    @classmethod
    def find_between(cls, section, start, end, limit=None, skip=None):
        """Return a list of slates between start and end, optionally
        limiting the number of results and/or skipping the first X results.
        """
        raise NotImplementedError()
        
