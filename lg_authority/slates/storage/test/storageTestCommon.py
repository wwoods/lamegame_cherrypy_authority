import os
import re
import time

import cherrypy
import lg_authority
from lg_authority.slates.storage import get_storage_class
from lg_authority.testutil import *

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

    def getStorage(self, name=None, timeout=None):
        """Gets a storage object that can be tested."""
        if name:
            name = 'test_' + self.storageName + '_' + name
        else:
            name = 'test_' + self.storageName + '_' + self.id()
        return self.storageClass('test', name, timeout=timeout)

    def test_isExpiredNonExisting(self):
        # Make sure that any non-existing slate is shown as expired until
        # it has something written to it.
        
        store = self.getStorage(timeout=60)
        self.assertTrue(store.is_expired())

        store.set('a', 'a')
        store = self.getStorage(timeout=60)
        self.assertFalse(store.is_expired())

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
        self.assertGreaterThan(59.9, ttl3)

