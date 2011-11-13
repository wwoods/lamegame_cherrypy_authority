
import unittest
import lg_authority
from lg_authority import Slate, AuthError
from lg_authority.tools import AuthTool
from lg_authority.authinterface import AuthInterface

class TestAuthInterface(unittest.TestCase):
    """Tests the authinterface"""

    def setUp(self):
        at = AuthTool()
        ma = at._merged_args({})
        at._setup_initialize(ma)
        self.ai = AuthInterface()

    def test_user_activate(self):
        # Also tests deactivate
        uname = 'testUser_activate'
        uid = self.ai.user_create(uname, {})
        self.assertEqual(None, Slate('user', uid).get('inactive'))
        self.ai.user_deactivate(uid)
        self.assertTrue(Slate('user', uid)['inactive'])
        self.ai.user_activate(uid)
        self.assertEqual(None, Slate('user', uid).get('inactive'))

    def test_user_create(self):
        uname = 'testUser'
        uid = self.ai.user_create(uname, {})
        self.assertFalse(Slate('user', uid).is_expired())
        self.assertFalse(Slate('username', uname).is_expired())
        self.assertEqual(uid, Slate('username', uname).get('userId'))

    if hasattr(unittest, 'skip'):
        @unittest.skip('Tested in test_user_activate')
        def test_user_deactivate(self):
            pass

    def test_user_delete(self):
        uname = 'testUser_delete'
        uid = self.ai.user_create(uname, {})
        self.ai.user_deactivate(uid)
        self.ai.user_delete(uid)
        self.assertTrue(Slate('user', uid).is_expired())
        self.assertTrue(Slate('username', uname).is_expired())

    def test_user_delete_notInactive(self):
        uname = 'testUser_delete_notInactive'
        uid = self.ai.user_create(uname, {})
        try:
            self.ai.user_delete(uid)
            self.fail("user_delete did not raise AuthError for active user")
        except AuthError:
            pass


