"""LameGame Productions' Slate implementation for CherryPy.

We use cherrypy.request to store some convenient variables as
well as data about the session for the current request. Instead of
polluting cherrypy.request we use a Session object bound to
cherrypy.session to store these variables.
"""

import datetime
import os
try:
  import cPickle as pickle
except ImportError:
  import pickle
import random
import time
import threading
import types
from warnings import warn

import cherrypy
from cherrypy.lib import httputil

from ..common import *

class Slate(object): #PY3 , metaclass=cherrypy._AttributeDocstrings):
    """A CherryPy dict-like Slate object (one per request for session state, 
    as well as any number of named slates).

    Slates are entirely lazy-loaded, meaning there should be no network
    overhead for calling Slate('section', 'name').  The writing of timestamps
    is also lazily written, meaning slates will expire after their specified 
    timeout unless touch() is called.

    Writing is accomplished only when a key's value is set directly - setting
    a key to an object and then altering the object will not save the
    changes to the object.

    The general network usage for a slate's life is:

    Slate():
        None
    First access call:
        Fetch timeout, expiration, any attributes in the 'cache' area of the
            site_storage_sections_{section} configuration.
        If expired, mark as expired but don't do anything.
    Each read call:
        If not expired, fetch specified data.  Else return default.
    Each write call:
        If expired, create new Slate storage with specified data and new
            expiration information.  Clear expired flag.
        Else, write new expiration and specified data
    """
    
    storage = None
    storage__doc = "Storage instance for this slate"
    
    def __init__(self, section, id, timeout={}):
        """Initializes the Slate, but does no work.

        Timeout -- int - Number of seconds after which to delete this slate's
            data (reset on each write), or None for no expiration.  Pass a
            dict (default param) to keep whatever the slate's current timeout
            is.
        """
        self.storage = config.storage_class(section, id, timeout)

    def is_expired(self):
        """Returns true if the Slate is expired or non-existant; otherwise
        returns false.
        """
        return self.storage.is_expired()

    def time_to_expire(self):
        """Returns the number of seconds before this Slate will expire.  This
        value is not refreshed after the first read!

        Returns None if already expired.  The minimum numeric value returned
        is 0.
        """
        return self.storage.time_to_expire()

    def expire(self):
        """Delete stored data; expire the session immediately."""
        self.storage.expire()

    def touch(self):
        """Renew the expiration date for this Slate, without writing any
        other data.
        """
        self.storage.touch()

    @classmethod
    def count_with(cls, section, key, value):
        """Return the number of slates who have value in the array keyed
        by key.  key must be in site_storage_sections_{section}'s index_lists
        parameter for the given section.
        """
        return config.storage_class.count_with(section, key, value)

    @classmethod
    def find_with(cls, section, key, value):
        """Return a list of slates having value in the array keyed by
        key.  key must be in site_storage_sections_{section}'s index_lists 
        parameter for the given section.
        """
        return config.storage_class.find_with(section, key, value)

    @classmethod
    def count_between(cls, section, start, end):
        """Returns the number of slates whose names are (inclusively) between
        start and end.
        """
        return config.storage_class.count_between(section, start, end)

    @classmethod
    def find_between(cls, section, start, end, limit=None, skip=None):
        """Return a list of slates between start (inclusive) and end 
        (exclusive).  Optionally limit the number of results returned and skip 
        the first X.
        """
        return config.storage_class.find_between(
            section, start, end, limit, skip
            )
    
    def __getitem__(self, key):
        result = self.storage.get(key, missing)
        if result is missing:
            raise KeyError(key)
        return result
    
    def __setitem__(self, key, value):
        self.storage.set(key, value)
    
    def __delitem__(self, key):
        result = self.storage.pop(key, missing)
        if result is missing:
            raise KeyError(key)

    def __contains__(self, key):
        result = self.storage.get(key, missing)
        if result is missing:
            return False
        return True

    def get(self, key, default=None):
        """Return the value for the specified key, or default"""
        return self.storage.get(key, default)
    
    def pop(self, key, default=None):
        """Remove the specified key and return the corresponding value.
        If key is not found, default is returned.
        """
        return self.storage.pop(key, default)
    
    def update(self, d):
        """D.update(E) -> None.  Update D from E: for k in E: D[k] = E[k]."""
        self.storage.update(d)
    
    def setdefault(self, key, default=None):
        """D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d if k not in D."""
        return self.storage.setdefault(key, default)
    
    def clear(self):
        """D.clear() -> None.  Remove all items from D."""
        self.storage.clear()
    
    def keys(self):
        """D.keys() -> list of D's keys."""
        return self.storage.keys()
    
    def items(self):
        """D.items() -> list of D's (key, value) pairs, as 2-tuples."""
        return self.storage.items()
    
    def values(self):
        """D.values() -> list of D's values."""
        return self.storage.values()

    def todict(self):
        """Slate -> dict"""
        return dict(self.storage.items())

    def set_timeout(self, timeout):
        """Change the timeout of this slate to the given timeout; the "touch"
        to effect the new timeout is not implicit.  Call touch() or do some
        write operation manually to overwrite the timeout.
        """
        self.storage.timeout = timeout

    def _get_section(self):
        return self.storage.section

    def _get_id(self):
        return self.storage.id

    section = property(_get_section)
    id__doc = """The slate name/ID.  Each unique name corresponds to a unique slate.  Fixation does not apply to slates - for instance, if a slate with the name 'user-testuser' is expired, then its data is erased, but that is still the name of the slate.
    """
    id = property(_get_id, doc=id__doc)

