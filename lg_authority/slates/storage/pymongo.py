import datetime
from .common import *

class PymongoStorage(SlateStorage):
    """Storing slates in MongoDb.

    Available params in storage_conf:
        host: Host address
        port: Port to connect with
        db: Database containing slates collection
        collection: Collection containing slates
    """

    conn = None
    conn__doc = "PyMongo collection object"

    def __init__(self, name, timeout, force_timeout):
        self.name = name
        self._cache = { 'auth': None }
        
        get_fields = {
            '_id': 1
            ,'timeout': 1
            ,'expire': 1
            ,'data.auth': 1
            }
        core = self.conn.find_one({ 'name': self.name }, get_fields)
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
            self.conn.save(new_dict)
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
                self.conn.update({ '_id': self._id }, updates)

    def __str__(self):
        return "PYMONGO{0}".format(self._id)

    def __repr__(self):
        return str(self)

    def set(self, key, value):
        pickled = pickle.dumps(value).encode('utf-8')

        if key in self._cache:
            self._cache[key] = pickled

        self.conn.update(
            { '_id': self._id }
            , { '$set': { 'data.' + key: pickled } }
            )

    def get(self, key, default):
        if key in self._cache:
            result = self._cache[key]
            if result is None:
                result = default
        else:
            doc = self.conn.find_one({ '_id': self._id }, { 'data.' + key: 1 })
            result = doc.get('data', {}).get(key, default)

        if result is not default:
            result = pickle.loads(str(result.decode('utf-8')))
        return result

    def pop(self, key, default):
        result = self.get(key, default)
        self.conn.update({ '_id': self._id }, { '$unset': { 'data.' + key: 1 } })
        return result

    def clear(self):
        self.conn.update({ '_id': self._id }, { '$unset': { 'data': 1 } })

    def keys(self):
        data = self.conn.find_one({ '_id': self._id }, { 'data': 1 })
        return data['data'].keys()

    def items(self):
        data = self.conn.find_one({ '_id': self._id }, { 'data': 1 })
        return data['data'].items()

    def values(self):
        data = self.conn.find_one({ '_id': self._id }, { 'data': 1 })
        return data['data'].values()
    
    def expire(self):
        self.conn.remove(self._id)

    @classmethod
    def setup(cls, conf):
        import pymongo
        c = pymongo.Connection(
          host=conf.get('host', None)
          ,port=conf.get('port', None)
          )
        d = c[conf['db']]
        cls.conn = d[conf['collection']]
        cls.conn.ensure_index([ ('name', 1) ], background=True)
        cls.conn.ensure_index([ ('expire', 1) ], background=True)

    @classmethod
    def is_expired(cls, name):
        doc = cls.conn.find_one({ 'name': name }, { 'expire': 1 })
        if doc is None:
            return True
        if doc['expire'] < datetime.datetime.utcnow():
            return True
        return False

    @classmethod
    def clean_up(cls):
        now = datetime.datetime.utcnow()
        cls.conn.remove({ 'expire': { '$lt': now } })
        log('Cleaned expired sessions')

