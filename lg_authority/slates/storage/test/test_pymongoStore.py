from lg_authority.testutil import LgTestCase
from .storageTestCommon import StorageTestCommon

class TestStoragePymongo(StorageTestCommon, LgTestCase):
    storageName = 'pymongo'
    storageConfig = {
        'db': 'lg_authority_tests'
        }

