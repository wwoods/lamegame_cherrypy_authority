from lg_authority.testutil import LgTestCase
from .storageTestCommon import StorageTestCommon

import os
testPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test.db') 

class TestStorageSqlite3(StorageTestCommon, LgTestCase):
    storageName = 'sqlite3'
    storageConfig = { 'file': testPath }

