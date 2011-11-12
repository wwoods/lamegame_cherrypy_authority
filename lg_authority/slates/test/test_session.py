import unittest

from lg_authority.tools import AuthTool
from lg_authority.slates.session import Session
from lg_authority.slates import Slate

class TestSession(unittest.TestCase):
    
    def setUp(self):
        at = AuthTool()
        ma = at._merged_args({ })
        AuthTool()._setup_initialize(ma)
        
        Slate('session', None).storage.destroySectionBeCarefulWhenYouCallThis(
            'session'
        )
        Slate('other', None).storage.destroySectionBeCarefulWhenYouCallThis(
            'other'
        )
        
    
    def test_diffCookieDiffStorage(self):
        s1 = Session('a', session_cookie='session')
        s1['var'] = 'value'
        s2 = Session(s1.id, session_cookie='other')
        self.assertNotEqual(s1['var'], s2.get('var'))
        self.assertTrue('var' in s1)
        self.assertTrue('var' not in s2)
        
        
    def test_regress_valueUpdate(self):
        s1 = Session('a', session_cookie='session')
        s1['var'] = 'value'
        s2 = Session(s1.id, session_cookie='session')
        self.assertEqual(s1['var'], s2.get('var'))
    