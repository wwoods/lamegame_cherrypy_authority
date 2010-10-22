import time
from .common import *

class RamStorage(SlateStorage):
    
    # Class-level objects. Don't rebind these!
    cache = {}

    def __init__(self, name, timeout):
        self.name = name
        if RamStorage.is_expired(name):
            self.record = self.cache[name] = {}
        else:
            self.record = self.cache.setdefault(name, {})

        self.record['timestamp'] = time.time()
        self.record['timeout'] = timeout
        self.data = self.record.setdefault('data', {})

    def __str__(self):
        return "RAM{0}".format(self.data)

    def __repr__(self):
        return str(self)

    def set(self, key, value):
        self.data[key] = value

    def get(self, key, default):
        return self.data.get(key, default)

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
        self._expire(self.name)

    @classmethod
    def is_expired(cls, name):
        obj = cls.cache.get(name, None)
        if obj is None:
            return True
        if obj['timeout'] is None:
            return False
        if obj['timestamp'] + obj['timeout'] * 60 < time.time():
            return True
        return False
    
    @classmethod
    def clean_up(cls):
        """Clean up expired sessions."""
        for id in list(cls.cache.keys()):
            if cls.is_expired(id):
                cls._expire(id)
        log('Cleaned expired sessions')

    @classmethod
    def _expire(cls, id):
        try:
            del cls.cache[id]
        except KeyError:
            pass
    
    def __len__(self):
        """Return the number of active sessions."""
        return len(self.cache)



