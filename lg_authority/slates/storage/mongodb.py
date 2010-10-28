import datetime
try:
    import cPickle as pickle
except ImportError:
    import pickle
from .common import *

class MongodbStorage(SlateStorage):
    """Storing slates in MongoDb.

    Available params in storage_conf:
        host: Host address
        port: Port to connect with
        db: Database containing slates collection
        collection_base: Collection base name to which '_' + Section is
            appended.  This is not the collection that is actually created.
    """

    def __init__(self, section, name, timeout, force_timeout):
        self.section = self._get_section(section)
        self.name = name
        self._cache = { 'auth': None }
        
        get_fields = {
            '_id': 1
            ,'timeout': 1
            ,'expire': 1
            ,'data.auth': 1
            }
        core = self.section.find_one({ 'name': self.name }, get_fields)
        now = datetime.datetime.utcnow()

        if core is None or core.get('expire', now) < now:
            new_dict = {
                'name': self.name
                ,'timeout': timeout
                ,'data': {}
                }
            if timeout is not None:
                new_dict['expire'] = now + datetime.timedelta(minutes=timeout)
            if core is not None:
                new_dict['_id'] = core['_id']
            self.section.save(new_dict)
            self._id = new_dict['_id']
        else:
            self._id = core['_id']
            self._cache.update(core.get('data', {}))

            #We also have to handle the case where timeout
            #has changed from/to None
            new_exp = missing
            if force_timeout:
                new_exp = timeout
            else:
                if 'expire' in core:
                    timeout = core.get('timeout', timeout)
                    half = core['expire'] - datetime.timedelta(minutes=timeout//2)
                    if half < now:
                        new_exp = timeout

            if new_exp is not missing:
                updates = {
                    '$set': {
                        'timeout': new_exp
                        }
                    }
                if new_exp is not None:
                    updates['$set']['expire'] = now + datetime.timedelta(minutes=new_exp)
                else:
                    updates['$unset'] = { 'expire': 1 }
                self.section.update({ '_id': self._id }, updates)

    def __str__(self):
        return "PYMONGO{0}".format(self._id)

    def __repr__(self):
        return str(self)

    def set(self, key, value):
        if key in self.section.lgauth_conf_indexed:
            pickled = value
        else:
            pickled = self.binary(pickle.dumps(value))

        if key in self._cache:
            self._cache[key] = pickled

        self.section.update(
            { '_id': self._id }
            , { '$set': { 'data.' + key: pickled } }
            )

    def get(self, key, default):
        if not isinstance(key, basestring):
            raise ValueError("Key must be string; was {0}".format(key))
        if key in self._cache:
            result = self._cache[key]
            if result is None:
                result = default
        else:
            doc = self.section.find_one({ '_id': self._id }, { 'data.' + key: 1 })
            result = doc.get('data', {}).get(key, default)

        if result is not default:
            result = self._get(key, result)
        return result

    def _get(self, key, value):
        """Translates the given value for the specified key into
        python objects (from pickle).
        """
        result = value
        if key not in self.section.lgauth_conf_indexed:
            result = pickle.loads(result)
        return result

    @classmethod
    def find_slates_with(cls, section, key, value):
        results = []
        section = cls._get_section(section)
        for result in section.find({ 'data.' + key: value }, { 'name': 1 }):
            results.append(result['name'])
        return results

    @classmethod
    def find_slates_between(cls, section, start, end, limit=None, skip=None):
        result = []
        section = cls._get_section(section)
        cursor = section.find(
            { 'name': { '$gte': start, '$lte': end } }, { 'name': 1 }
            ).sort(
            [ ('name',1) ]
            )
        skip = skip or 0
        limit = skip + limit if limit else None
        return [ d['name'] for d in cursor[skip:limit] ]

    def pop(self, key, default):
        result = self.get(key, default)
        self.section.update({ '_id': self._id }, { '$unset': { 'data.' + key: 1 } })
        return result

    def clear(self):
        self.section.update({ '_id': self._id }, { '$unset': { 'data': 1 } })

    def items(self):
        data = self.section.find_one({ '_id': self._id }, { 'data': 1 })
        itms = data['data'].items()
        return [ (k,self._get(k,v)) for k,v in itms ]

    def expire(self):
        self.section.remove(self._id)

    @classmethod
    def setup(cls, conf):
        import pymongo
        c = pymongo.Connection(
          host=conf.get('host', None)
          ,port=conf.get('port', None)
          )
        cls.db = c[conf['db']]
        cls.collection_base = conf['collection_base']
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

        result = cls.db[cls.collection_base + '_' + section]
        result.ensure_index([ ('name', 1) ], unique=True, background=True)
        result.ensure_index([ ('expire', 1) ], background=True)

        options = cls.get_section_config(section)
        result.lgauth_conf_indexed = options.get('index_lists', [])
        for index in result.lgauth_conf_indexed:
            result.ensure_index([ ('data.' + index, 1) ], background=True)

        cls.collections[section] = result
        return result

    @classmethod
    def is_expired(cls, section, name):
        section = cls._get_section(section)
        doc = section.find_one({ 'name': name }, { 'expire': 1 })
        if doc is None:
            return True
        now = datetime.datetime.utcnow()
        if doc.get('expire', now) < now:
            return True
        return False

    @classmethod
    def clean_up(cls):
        now = datetime.datetime.utcnow()
        for section in cls.collections.values():
            section.remove({ 'expire': { '$lt': now } })
        log('Cleaned expired slates')

