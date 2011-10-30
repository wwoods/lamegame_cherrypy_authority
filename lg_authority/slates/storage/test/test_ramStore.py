from lg_authority.testutil import LgTestCase
from .storageTestCommon import StorageTestCommon

class TestStorageRam(StorageTestCommon, LgTestCase):
    storageName = 'ram'
    storageConfig = { }

