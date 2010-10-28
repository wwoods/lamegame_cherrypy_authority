"""LameGame Productions' Slate implementation for CherryPy.

We use cherrypy.request to store some convenient variables as
well as data about the session for the current request. Instead of
polluting cherrypy.request we use a Session object bound to
cherrypy.session to store these variables.

Also provides cherrypy.slate[] to retrieve a named slate.

Call cherrypy.session.expire() to force a session to expire.
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
    """A CherryPy dict-like Slate object (one per request for session state, as well as any number of named slates).

    Writing is accomplished only when set() is called, setdefault() is called, or an item is written (Slate['key'] = 'value').
    """
    
    name = None
    name__doc = """The slate name/ID.  Each unique name corresponds to a unique slate.  Fixation does not apply to slates - for instance, if a slate with the name 'user-testuser' is expired, then its data is erased, but that is still the name of the slate.
    """
    
    timeout = None
    timeout__doc = "Number of minutes after which to delete slate data, or None for no expiration.  The default for named slates is no expiration.  The default for sessions is one hour."

    storage = None
    storage__doc = "Storage instance for this slate"
    
    def __init__(self, section, name, timeout=missing, force_timeout=False):
        """Initializes the Slate, and wipes expired data if necessary.
        Also updates the Slate's Expiration date if needed.

        Will only update the Slate's timeout if either the slate is new (or
        previously expired), or the force_timeout parameter is set to True.
        """
        self.section = section
        self.name = name
        self._data = {}
        
        if not timeout is missing:
            self.timeout = timeout

        self.storage = config.storage_class(self.section, self.name, self.timeout, force_timeout)
        log('Slate loaded: {0}'.format(repr(self.storage)))

    @classmethod 
    def lookup(cls, section, name):
        """Fetch the specified slate, but if it does not exist or is expired,
        return None instead of creating it.
        """
        if cls.is_expired(section, name):
            return None
        return Slate(section, name)

    @classmethod
    def is_expired(cls, section, name):
        """Returns True if the given Slate identifier is expired or non-existant."""
        return config.storage_class.is_expired(section, name)

    @classmethod
    def count_slates_with(cls, section, key, value):
        """Return the number of slates who have value in the array keyed
        by key.  key must be in site_storage_sections_{section}'s index_lists
        parameter for the given section.
        """
        return config.storage_class.count_slates_with(section, key, value)

    @classmethod
    def find_slates_with(cls, section, key, value):
        """Return a list of slate names having value in the array keyed by
        key.  key must be in site_storage_sections_{section}'s index_lists 
        parameter for the given section.
        """
        return config.storage_class.find_slates_with(section, key, value)

    @classmethod
    def count_slates_between(cls, section, start, end):
        """Returns the number of slates whose names are (inclusively) between
        start and end.
        """
        return config.storage_class.count_slates_between(section, start, end)

    @classmethod
    def find_slates_between(cls, section, start, end, limit=None, skip=None):
        """Return a list of slate names between start and end.  Optionally
        limit the number of results returned and skip the first X.
        """
        return config.storage_class.find_slates_between(
            section, start, end, limit, skip
            )

    def expire(self):
        """Delete stored session data."""
        self.storage.expire()
    
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

