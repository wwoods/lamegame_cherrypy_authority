import unittest

from lg_authority.tools import AuthTool
from lg_authority.slates.session import Session

class TestSession(unittest.TestCase):
    
    def setUp(self):
        at = AuthTool()
        ma = at._merged_args({ })
        AuthTool()._setup_initialize(ma)
        
        Session('a').storage.destroySectionBeCarefulWhenYouCallThis('session')
        Session('a').storage.destroySectionBeCarefulWhenYouCallThis('other')
        
    
    def test_diffCookieDiffStorage(self):
        s1 = Session('a')
        s1['var'] = 'value'
        s2 = Session(s1.id, session_cookie='other')
        self.assertNotEqual(s1['var'], s2.get('var'))
        self.assertTrue('var' in s1)
        self.assertTrue('var' not in s2)
        
        
    def test_regress_valueUpdate(self):
        s1 = Session('a')
        s1['var'] = 'value'
        s2 = Session(s1.id)
        self.assertEqual(s1['var'], s2.get('var'))
    