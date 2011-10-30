import datetime
try:
    import cPickle as pickle
except ImportError:
    import pickle
from .common import *
from ..slates import Slate

class PymongoStorage(SlateStorage):
    """Storing slates in MongoDb.

    Available params in storage_conf:
        host: Host address
        port: Port to connect with
        db: Database containing slates collection
        collection_base: Collection base name to which the Section name is
            appended.  This is not the collection that is actually created.
            If not specified, presumed the empty string.
    """

    def __init__(self, section, id, timeout):
        self.section = section
        self.id = id
        self.timeout = timeout
        self._section = self._get_section(self.section)
        self._conf = self.get_section_config()
    
    def _expired(self):
        """Call to set this Slate's local state as expired"""
        self.expired = True
        self._id = None
        for j in self.cache.keys():
            self.cache[j] = missing

    def _access(self):
        """Called before access of any type"""
        if hasattr(self, '_first_access'):
            return
        self._first_access = True

        core = self._section.find_one({ 'name': self.id })
        now = datetime.datetime.utcnow()

        if core is None or core.get('expire', now) < now:
            self.cache = {}
            self._expired()
            if core is not None:
                self._id = core['_id']
            else:
                self._id = None
            self.expiry = None
            log('Loaded new {1}slate: {0}'.format(
                self.id
                , '(expired; overwriting) '.format(self._id) 
                    if self._id is not None 
                    else ''
                ))
        else:
            self.expired = False
            self._id = core['_id']
            self.cache = core.get('data', {})
            for k,v in self.cache.items():
                self.cache[k] = self._get(k,v)
            self.expiry = core.get('expire', None)
            if isinstance(self.timeout, dict):
                self.timeout = core.get('timeout', None)
            log('Loaded slate {1} with {0}'.format(self.cache, self.id))

    def _write(self, fields=None):
        """Called before any write operation to setup the storage.
        Implicitly calls _access(), then writes either a brand
        new record or updates the old one, depending on expired status.

        fields may be set to a dict to also set those values (in addition
        to the timeout)
        """
        self._access()

        fields = fields or {}

        for k,v in fields.items():
            self.cache[k] = v

        useTimeout = not isinstance(self.timeout, dict)

        if self.expired:
            if not useTimeout:
                #We don't have a valid timeout, and we're new...
                raise ArgumentError("Must specify a timeout for new slates")

            new_dict = {
                'name': self.id
                ,'data': {}
                }
            if useTimeout:
                new_dict['timeout'] = self.timeout
                if self.timeout is not None:
                    new_dict['expire'] = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.timeout)
            if self._id is not None:
                new_dict['_id'] = self._id
            for k,v in fields.items():
                new_dict['data'][k] = self._set(k,v)
            self._section.save(new_dict)
            self._id = new_dict['_id']
            self.expired = False
        else:
            updates = {}
            sets = updates['$set'] = {}
            unsets = updates['$unset'] = {}

            if not useTimeout:
                raise Exception("Code assertion failure - we must have a " +
                    "timeout to be here.")

            sets['timeout'] = self.timeout
            if self.timeout is not None:
                sets['expire'] = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.timeout)
            else:
                unsets['expire'] = 1

            for k,v in fields.items():
                if v is missing:
                    unsets['data.' + k] = 1
                else:
                    sets['data.' + k] = self._set(k, v)

            self._section.update({ '_id': self._id }, updates)

    def __str__(self):
        return "PYMONGO({0})".format(self.id)

    def __repr__(self):
        return str(self)

    def touch(self):
        self._write()

    def set(self, key, value):
        self._write({ key: value })

    def _set(self, key, value):
        """Translates a python value into one suitable for mongodb storage"""
        if key in self._section.lgauth_conf_indexed:
            pickled = value
        else:
            pickled = self.binary(pickle.dumps(value))

        return pickled

    def get(self, key, default):
        if not isinstance(key, basestring):
            raise ValueError("Key must be string; was {0}".format(key))

        self._access()
        if self.expired:
            return default
        if key in self.cache:
            result = self.cache[key]
            if result is missing:
                result = default
        else:
            result = default
        return result

    def _get(self, key, value):
        """Translates the given value for the specified key into
        python objects (from pickle).
        """
        result = value
        if key not in self._section.lgauth_conf_indexed:
            result = pickle.loads(result)
        return result

    def pop(self, key, default):
        result = self.get(key, default)
        self._write({ key: missing })
        return result

    def clear(self):
        self._write()
        self._section.update({ '_id': self._id }, { '$set': { 'data': {} } })

    def items(self):
        self._access()
        if self.expired:
            return []
        return self.cache.copy()

    def expire(self):
        self._access()
        self._section.remove(self._id)
        self._expired()

    def is_expired(self):
        self._access()
        return self.expired

    def time_to_expire(self):
        self._access()
        if self.expired:
            return 0
        if not hasattr(self, 'expiry'):
            return None
        diff = self.expiry - datetime.datetime.utcnow()
        diff = diff.days * 3600 * 24 + diff.seconds + diff.microseconds * 1e-6
        return max(0, diff)

    @classmethod
    def destroySectionBeCarefulWhenYouCallThis(cls, section):
        """DO NOT call this unless you know what you are doing, or are 
        a test environment.
        """
        s = cls._get_section(section)
        s.remove()

    @classmethod
    def find_with(cls, section, key, value):
        results = []
        _section = cls._get_section(section)
        for result in _section.find({ 'data.' + key: value }, { 'name': 1 }):
            results.append(Slate(section, result['name']))
        return results

    @classmethod
    def find_between(cls, section, start, end, limit=None, skip=None):
        result = []
        _section = cls._get_section(section)
        cursor = _section.find(
            { 'name': { '$gte': start, '$lt': end } }, { 'name': 1 }
            ).sort(
            [ ('name',1) ]
            )
        skip = skip or 0
        limit = skip + limit if limit else None
        return [ Slate(section, d['name']) for d in cursor[skip:limit] ]

    @classmethod
    def setup(cls, conf):
        import pymongo
        c = pymongo.Connection(
          host=conf.get('host', None)
          ,port=conf.get('port', None)
          )
        cls.db = c[conf['db']]
        cls.collection_base = conf.get('collection_base', '')
        cls.collections = {}

        from bson.binary import Binary
        cls.binary = Binary

    @classmethod
    def _get_section(cls, section):
        """Returns a pymongo.Collection representing the requested section
        """
        result = cls.collections.get(section)
        if result is not None:
            return result

        result = cls.db[cls.collection_base + section]
        result.ensure_index([ ('name', 1) ], unique=True, background=True)
        result.ensure_index([ ('expire', 1) ], background=True)

        options = cls._get_section_config(section)
        result.lgauth_conf_indexed = options.get('index_lists', [])
        for index in result.lgauth_conf_indexed:
            result.ensure_index([ ('data.' + index, 1) ], background=True)

        cls.collections[section] = result
        return result

    @classmethod
    def clean_up(cls):
        now = datetime.datetime.utcnow()
        for section in cls.collections.values():
            section.remove({ 'expire': { '$lt': now } })
        log('Cleaned expired slates')

