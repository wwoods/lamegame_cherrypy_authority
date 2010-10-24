import time
from .common import *

class RamStorage(SlateStorage):
    
    # Class-level objects. Don't rebind these!
    section_cache = {}

    def __init__(self, section, name, timeout, force_timeout):
        self.section_name = section
        self.section = self.section_cache.setdefault(section, {})
        self.name = name
        if RamStorage.is_expired(section, name):
            self.record = self.section[name] = { 'timeout': timeout }
        else:
            self.record = self.section[name]
            if force_timeout:
                self.record['timeout'] = timeout

        if self.record['timeout'] is not None:
            self.record['expires'] = time.time() + 60 * self.record['timeout']
        self.data = self.record.setdefault('data', {})

    def __str__(self):
        return "RAM{0}".format(self.data)

    def __repr__(self):
        return str(self)

    def set(self, key, value):
        self.data[key] = value

    def get(self, key, default):
        return self.data.get(key, default)

    @classmethod
    def find_slates_with(cls, section, key, value):
        result = []
        for k,v in cls.section_cache.get(section, {}).items():
            d = v.get('data', {})
            if value in d.get(key, []):
                result.append(k)

        return result

    def pop(self, key, default):
        return self.data.pop(key, default)

    def clear(self):
        self.data = self.record['data'] = {}

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def values(self):
        return self.data.values()
    
    def expire(self):
        self._expire(self.section_name, self)

    @classmethod
    def is_expired(cls, section, name):
        obj = cls.section_cache.get(section, {}).get(name, None)
        if obj is None:
            return True
        if obj['timeout'] is None:
            return False
        if obj['expires'] < time.time():
            return True
        return False
    
    @classmethod
    def clean_up(cls):
        """Clean up expired sessions."""
        for s,c in list(cls.section_cache.items()):
            for id in list(c.keys()):
                if cls.is_expired(s, id):
                    cls._expire(c, s, c[id])
        log('Cleaned expired sessions')

    @classmethod
    def _expire(cls, section, slate):
        """Utility function to expire a certain slate.  
        slate is the Slate object, section is the section key.
        """
        try:
            del cls.section_cache[section][slate.name]
        except KeyError:
            pass
    
    def __len__(self):
        """Return the number of active sessions."""
        return len(self.cache)

