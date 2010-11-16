import time
from .common import *
from ..slates import Slate

class RamStorage(SlateStorage):
    
    # Class-level objects. Don't rebind these!
    section_cache = {}

    def __init__(self, section, id, timeout, force_timeout):
        self.section = section
        self.section_store = self.section_cache.setdefault(section, {})
        self.id = id
        self.timeout = timeout
        self.force_timeout = force_timeout

    def _expired(self):
        """Sets this object up so that it has expired."""
        self.expired = True
        self.data = {}

    def _access(self):
        """Called before access of any type"""
        if hasattr(self, '_first_access'):
            return
        self._first_access = True

        section = self.section
        id = self.id

        if RamStorage._is_expired(section, id):
            self._expired()
            log('Loaded new (expired) slate')
        else:
            self.expired = False
            if not self.force_timeout:
                self.timeout = self.section_store[id]['timeout']
            self.data = self.section_store[id]['data']
            self.expiry = self.section_store[id].get('expire', None)
            log('Loaded slate with {0}'.format(self.data))

    def _write(self):
        """Called before any write operation to setup the storage.
        Implicitly calls _access().
        """
        self._access()

        if self.expired:
            self.record = self.section_store[self.id] = {}
            self.record['timeout'] = self.timeout
            self.expired = False
        else:
            self.record = self.section_store[self.id]
            if self.force_timeout:
                self.record['timeout'] = self.timeout

        if self.record['timeout'] is not None:
            self.record['expire'] = time.time() + self.record['timeout']
        else:
            self.record.pop('expire', None)

        self.data = self.record.setdefault('data', {})

    def __str__(self):
        self._access()
        return "RAM{0}".format(self.data or '(empty)')

    def __repr__(self):
        return str(self)

    def touch(self):
        self._write()

    def set(self, key, value):
        self._write()
        self.data[key] = value

    def get(self, key, default):
        self._access()
        return self.data.get(key, default)

    def pop(self, key, default):
        self._write()
        return self.data.pop(key, default)

    def clear(self):
        self._write()
        self.data = self.record['data'] = {}

    def keys(self):
        self._access()
        return self.data.keys()

    def items(self):
        self._access()
        return self.data.items()

    def values(self):
        self._access()
        return self.data.values()
    
    def expire(self):
        self._expire(self.section, self)
        self._expired()

    def is_expired(self):
        self._access()
        return self.expired

    def time_to_expire(self):
        if self.expired:
            return None
        if not hasattr(self, 'expiry'):
            return None
        return max(0, self.expiry - time.time())

    @classmethod
    def find_with(cls, section, key, value):
        result = []
        for k,v in cls.section_cache.get(section, {}).items():
            d = v.get('data', {})
            if value in d.get(key, []):
                result.append(Slate(section, k))

        return result

    @classmethod
    def find_between(cls, section, start, end, limit=None, skip=None):
        sec = cls.section_cache.get(section, {}).keys()
        sec = [ s for s in sec if start <= s and s < end ]
        sec.sort()
        if skip is None:
            skip = 0
        if limit is None:
            limit = len(sec) - skip
        return [ Slate(section, s) for s in sec[skip:skip + limit] ]

    @classmethod
    def _is_expired(cls, section, name):
        obj = cls.section_cache.get(section, {}).get(name, None)
        if obj is None:
            return True
        if obj['timeout'] is None:
            return False
        if obj['expire'] < time.time():
            return True
        return False
    
    @classmethod
    def clean_up(cls):
        """Clean up expired slates."""
        for s,c in list(cls.section_cache.items()):
            for id in list(c.keys()):
                if cls.is_expired(s, id):
                    cls._expire(c, s, c[id])
        log('Cleaned expired slates')

    @classmethod
    def _expire(cls, section, slate):
        """Utility function to expire a certain slate.  
        slate is the Slate object, section is the section key.
        """
        try:
            del cls.section_cache[section][slate.id]
        except KeyError:
            pass
    
    def __len__(self):
        """Return the number of active sessions."""
        return len(self.cache)

