from lg_authority.testutil import LgTestCase
from .storageTestCommon import StorageTestCommon

class TestStorageSqlite3(StorageTestCommon, LgTestCase):
    storageName = 'sqlite3'
    storageConfig = { 'file': '/var/tmp/lg_authority_test.sqlite3' }

