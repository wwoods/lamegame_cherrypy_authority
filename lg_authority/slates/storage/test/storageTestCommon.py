import os
import re
import time

import cherrypy
import lg_authority
from lg_authority.slates.storage import get_storage_class
from lg_authority.testutil import *

missing = {}

class StorageTestCommon(object):
    """Storage tests.  Cannot derive from TestCase or would be ran as a test.
    All derivatives should also derive from lg_authority.testutil.LgTestCase.
    """
    storageName = None
    storageName__doc = "The name of this class' storage type"

    storageConfig = None
    storageConfig__doc = "Config dict passed to StorageClass.setup()"

    def setUp(self):
        self.storageClass = get_storage_class(self.storageName)
        self.storageClass.setup(self.storageConfig)
        self.storageClass.destroySectionBeCarefulWhenYouCallThis('test')

    def getStorage(self, name=missing, timeout=None):
        """Gets a storage object that can be tested."""
        if name is missing:
            name = 'test_' + self.storageName + '_' + self.id()
        elif name is not None:
            name = 'test_' + self.storageName + '_' + name
        return self.storageClass('test', name, timeout=timeout)

    def test_clear(self):
        store = self.getStorage()
        store.set('a', 'b')
        store.set('b', 'c')
        store.clear()
        self.assertEqual([], store.items())

        store = self.getStorage()
        self.assertEqual([], store.items())

    def test_concurrentWrite(self):
        #Multiple changes must go through.  That's the whole point of slates.
        #Load everything, write only what you need.
        store = self.getStorage()
        store.touch() # Make it unexpired to simulate simulataneous requests
        store2 = self.getStorage()
        store2.touch() # Ensure everything's loaded up

        store.set('a', 'b')
        store2.set('b', 'a')

        # We don't expect them to update local cache from each other... that
        # would just be inefficient.  While this seems like a silly thing
        # to test for e.g. ram slates, it's nice to have consistent behavior.
        self.assertEqual([ ('a', 'b') ], store.items())
        self.assertEqual([ ('b', 'a') ], store2.items())

        store = self.getStorage()
        self.assertEqual([ ('a', 'b'), ('b', 'a') ], store.items())

    def test_expire(self):
        store = self.getStorage()
        store.set('a', 'b')
        store.expire()
        self.assertTrue(store.is_expired())
        self.assertEqual(None, store.get('a', None))

        store = self.getStorage()
        self.assertTrue(store.is_expired())
        self.assertEqual(None, store.get('a', None))

    def test_isExpiredNonExisting(self):
        # Make sure that any non-existing slate is shown as expired until
        # it has something written to it.
        
        store = self.getStorage(timeout=60)
        self.assertTrue(store.is_expired())

        store.set('a', 'a')
        store = self.getStorage(timeout=60)
        self.assertFalse(store.is_expired())

    def test_items(self):
        """items() works"""
        store = self.getStorage()
        store.set('a', 'b')
        store.set('b', 'c')
        self.assertEqual([ ('a', 'b'), ('b', 'c') ], store.items())

        store = self.getStorage()
        self.assertEqual([ ('a', 'b'), ('b', 'c') ], store.items())

    def test_newId(self):
        """Slates can be initialized with no id; one will be assigned"""

        store = self.getStorage(None)
        self.assertEqual(None, store.id)
        self.assertTrue(store.is_expired())

        store.touch()
        self.assertNotEqual(None, store.id)
        self.assertFalse(store.is_expired())

        #Create a 2nd one just to make sure the ids are different...
        store2 = self.getStorage(None)
        self.assertNotEqual(store.id, store2.id)

    def test_pop(self):
        store = self.getStorage()
        store.set('a', 'b')
        self.assertEqual('b', store.pop('a', None))
        self.assertEqual(None, store.pop('a', None))

        store = self.getStorage()
        self.assertEqual(None, store.pop('a', None))

    def test_setAndGet(self):
        # Test that set and get work
        store = self.getStorage(timeout=60)
        store.set('j', 56)
        self.assertEqual(56, store.get('j', None))

        store = self.getStorage(timeout=60)
        self.assertEqual(56, store.get('j', None))

    def test_timeoutValues(self):
        # Test that the different timeout meanings catch on
        store = self.getStorage(timeout=60)
        store.touch()

        # Should keep timeout
        store = self.getStorage(timeout={})
        store.set('a', 'b')
        self.assertEqual(store.timeout, 60)

        # Should change timeout
        store = self.getStorage(timeout=20)
        store.set('c', 'd')
        self.assertEqual(store.timeout, 20)

    def test_touch(self):
        # Make sure that touch updates the timestamp
        # Create the slate storage
        store = self.getStorage(timeout=60)
        store.touch()

        # Check the time to live
        store = self.getStorage(timeout=60)
        ttl1 = store.time_to_expire()

        time.sleep(0.5)

        # Make sure it trends downwards
        store = self.getStorage(timeout=60)
        ttl2 = store.time_to_expire()

        self.assertLessThan(ttl1, ttl2)

        # Touch it and make sure it expires in 60 seconds again
        store.touch()
        store = self.getStorage(timeout=60)
        ttl3 = store.time_to_expire()
        self.assertGreaterThan(59.8, ttl3)

