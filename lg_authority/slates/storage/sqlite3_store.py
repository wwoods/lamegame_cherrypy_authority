import datetime
import threading
import uuid
try:
    import cPickle as pickle
except ImportError:
    import pickle
from .common import *
from ..slates import Slate

try:
    my_buffer = buffer
    has_buffer = True
except NameError:
    my_buffer = bytes
    has_buffer = False

class Sqlite3Storage(SlateStorage):
    """Storing slates in SqlLite (file-based).

    Available params in storage_conf:
        file: The sqlite database file.
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
        for j in self.cache.keys():
            self.cache[j] = missing

    def _access(self):
        """Called before access of any type"""
        if hasattr(self, '_first_access'):
            return
        self._first_access = True

        db = self._get_db()
        try:
            cur = db.cursor()
            cur.execute("""SELECT id,timeout,expire FROM "{0}" WHERE id = ?""".format(self.section), (self.id,))
            core = cur.fetchone()

            now = datetime.datetime.utcnow()
            self.cache = {}
    
            if core is None or (core[2] is not None and core[2] < now):
                self._expired()
                if core is not None:
                    self.expired = 'existed'
                log('Loaded new {1}slate: {0}'.format(
                    self.id
                    , '(expired) ' if core is not None else ''
                    ))
            else:
                self.expired = False
                self.expiry = core[2]
    
                #Fetch data elements
                cur.execute("""SELECT key,value FROM "{0}_data" WHERE id = ?""".format(self.section), (self.id,))
                vals = cur.fetchall()
                for k,v in vals:
                    self.cache[k] = self._get(k, v)

                if isinstance(self.timeout, dict):
                    self.timeout = core[1]
    
                log('Loaded slate {1} with {0}'.format(self.cache, self.id))
                
        finally:
            cur.close()

    def _write(self, fields=None):
        """Called before any write operation to setup the storage.
        Implicitly calls _access(), then writes either a brand
        new record or updates the old one, depending on expired status.

        fields may be set to a dict to also set those values.
        """
        self._access()

        fields = fields or {}

        for k,v in fields.items():
            self.cache[k] = v

        if isinstance(self.timeout, dict):
            if self.expired:
                raise ArgumentError("Must specify a timeout for new slates")
            else:
                raise ArgumentError("Code assertion - should have timeout")

        db = self._get_db()
        with db:
            cur = db.cursor()

            if self.expired:
                if self.expired == 'existed':
                    self._clear_slate(self.section, self.id, True)
                if self.id is None:
                    self.id = Sqlite3Storage.generateId()
                new_vals = [self.id, self.timeout, None]
                if self.timeout is not None:
                    new_vals[2] = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.timeout)

                cur.execute("""INSERT INTO "{0}" (id,timeout,expire) VALUES (?,?,?)""".format(self.section), new_vals)
            else:
                new_vals = [self.timeout, None, self.id]
                if self.timeout is not None:
                    new_vals[1] = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.timeout)
                cur.execute("""UPDATE "{0}" SET timeout=?, expire=? WHERE id=?""".format(self.section), new_vals)

            #Now update our values
            for k,v in fields.items():
                cur.execute("""DELETE FROM "{0}_data" WHERE id = ? AND key = ?""".format(self.section), (self.id,k))
                if k in self._conf.get('index_lists', []):
                    cur.execute("""DELETE FROM "{0}_index" WHERE id = ? AND key = ?""".format(self.section), (self.id,k))
                    for v2 in v:
                        cur.execute("""INSERT INTO "{0}_index" (id,key,value) VALUES (?,?,?)""".format(self.section), (self.id,k,v2))
                nv = self._set(k, v)
                cur.execute("""INSERT INTO "{0}_data" (id,key,value) VALUES (?,?,?)""".format(self.section), (self.id,k,nv))

            self.expired = False

    def __str__(self):
        return "SQLITE({0})".format(self.id)

    def __repr__(self):
        return str(self)

    def touch(self):
        self._write()

    def set(self, key, value):
        self._write({ key: value })

    def _set(self, key, value):
        """Translates a python value into one suitable for storage"""
        pickled = my_buffer(pickle.dumps(value))
        return pickled

    def get(self, key, default):
        if not isinstance(key, basestring):
            raise ValueError("Key must be string; was {0}".format(key))

        self._access()
        if self.expired:
            log('WARNING: GETTING FROM EXPIRED')
            return default
        if key in self.cache:
            result = self.cache[key]
            if result is missing:
                result = default
        else:
            db = self._get_db()
            try:
                cur = db.cursor()
                cur.execute("""SELECT value FROM "{0}_data" WHERE id = ? AND key = ?""".format(self.section), (self.id,key))
                result = cur.fetchone()
                if result is None:
                    result = default
                else:
                    result = self._get(key, result[0])
            finally:
                cur.close()
        return result

    def _get(self, key, value):
        """Translates the given value for the specified key into
        python objects (from pickle).
        """
        if not isinstance(value, my_buffer):
            raise ValueError('Value is not buffer; is {0}'.format(type(value)))
        if has_buffer:
            value = str(value)
        result = pickle.loads(value)
        return result

    def pop(self, key, default):
        self._access()
        db = self._get_db()
        try:
            cur = db.cursor()
            cur.execute("""SELECT value FROM "{0}_data" WHERE id = ? AND key = ?""".format(self.section), (self.id,key))
            data = cur.fetchall()
            if len(data) == 1:
                result = self._get(key, data[0][0])
            else:
                result = default

            cur.execute("""DELETE FROM "{0}_data" WHERE id = ? AND key = ?""".format(self.section), (self.id,key))
            db.commit()

            try:
                del self.cache[key]
            except KeyError:
                pass

            return result
        finally:
            cur.close()

    def clear(self):
        self._clear_slate(self.section, self.id)
        self.cache = {}

    def items(self):
        self._access()
        if self.expired:
            return []
        return self.cache.items()

    def expire(self):
        self._access()
        self._clear_slate(self.section, self.id, True)
        self.cache = {}
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
        db = cls._get_db()
        try:
            cur = db.cursor()
            cur.execute(
                """DROP TABLE IF EXISTS "{0}_index" """.format(section)
                )
            cur.execute(
                """DROP TABLE IF EXISTS "{0}_data" """.format(section)
                )
            cur.execute(
                """DROP TABLE IF EXISTS "{0}" """.format(section)
                )
            db.commit()
        finally:
            cur.close()

    @classmethod
    def find_with(cls, section, key, value):
        db = cls._get_db()
        try:
            cur = db.cursor()
            cur.execute("""SELECT id FROM "{0}_index" WHERE key = ? AND value = ?""".format(section), (key, value))
            rows = cur.fetchall()
            return [ Slate(section, row[0]) for row in rows ]
        finally:
            cur.close()

    @classmethod
    def find_between(cls, section, start, end, limit=None, skip=None):
        db = cls._get_db()
        try:
            cur = db.cursor()
            cur.execute("""SELECT id FROM "{0}" WHERE id >= ? AND id < ?""".format(section), (start, end))
            rows = cur.fetchall()
            skip = skip or 0
            limit = skip + limit if limit else None
            return [ Slate(section, row[0]) for row in rows ]
        finally:
            cur.close()

    @classmethod
    def generateId(cls):
        """Generates a UUID for a new slate that has no ID"""
        return uuid.uuid4().hex

    @classmethod
    def setup(cls, conf):
        import sqlite3

        cls.storage = threading.local()
        cls.storage_file = conf.get('file', ':memory:')
        cls.storage_checked = []
        
    @classmethod
    def _get_db(cls):
        db = getattr(cls.storage, 'db', None)
        if db is None:
            import sqlite3
            db = cls.storage.db = sqlite3.Connection(cls.storage_file, detect_types=sqlite3.PARSE_DECLTYPES)
        return db

    @classmethod
    def _get_section(cls, section):
        """Returns the table base name representing the requested section.
        If not already exists, create it and all supplementary tables.
        """
        db = cls._get_db()
        try:
            cur = db.cursor()

            already_queried = section in cls.storage_checked
            if not already_queried and cur.execute("SELECT COUNT(*) FROM SQLite_Master WHERE type='table' AND name=?", (section,)).fetchone()[0] != 1:
                #Create tables
                cls.storage_checked.append(section)
                cur.execute("""CREATE TABLE "{0}" (id TEXT, timeout INTEGER, expire TIMESTAMP)""".format(section))
                cur.execute("""CREATE UNIQUE INDEX "{0}_pk" ON "{0}" (id ASC)""".format(section))
                cur.execute("""CREATE INDEX "{0}_expire" ON "{0}" (expire DESC)""".format(section))

                cur.execute("""CREATE TABLE "{0}_data" (id TEXT, key TEXT, value BLOB)""".format(section))
                cur.execute("""CREATE UNIQUE INDEX "{0}_data_pk" ON "{0}_data" (id ASC, key ASC)""".format(section))

                cur.execute("""CREATE TABLE "{0}_index" (id TEXT, key TEXT, value TEXT)""".format(section))
                cur.execute("""CREATE INDEX "{0}_index_pk" ON "{0}_index" (id ASC)""".format(section))
                cur.execute("""CREATE INDEX "{0}_index_search" ON "{0}_index" (key ASC, value ASC)""".format(section))

                db.commit()

            return section
        finally:
            cur.close()

    @classmethod
    def _clear_slate(cls, section, id, expire=False):
        section = cls._get_section(section)
        db = cls._get_db()
        try:
            cur = db.cursor()
            id_tuple = (id,)
            cur.execute("""DELETE FROM "{0}_data" WHERE id = ?""".format(section), id_tuple)
            cur.execute("""DELETE FROM "{0}_index" WHERE id = ?""".format(section), id_tuple)
            if expire:
                cur.execute("""DELETE FROM "{0}" WHERE id = ?""".format(section), id_tuple)
            db.commit()
        finally:
            cur.close()

    @classmethod
    def clean_up(cls):
        now = datetime.datetime.utcnow()
        db = cls._get_db()
        for section in cls.storage_checked:
            try:
                cur = db.cursor()
                rows = cur.execute("""SELECT id FROM "{0}" WHERE expire < ?""".format(section), (now,)).fetchall()
                cur.executemany("""DELETE FROM "{0}" WHERE id = ?""".format(section), rows)
                cur.executemany("""DELETE FROM "{0}_data" WHERE id = ?""".format(section), rows)
                cur.executemany("""DELETE FROM "{0}_index" WHERE id = ?""".format(section), rows)
                db.commit()
            finally:
                cur.close()
        log('Cleaned expired slates')

