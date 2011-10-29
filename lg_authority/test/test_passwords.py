import unittest

from lg_authority.passwords import *

class TestPasswords(unittest.TestCase):
    def test_check_complexity_short(self):
        """Ensure that bat, cow, barf, 89btw complain about length"""
        for pword in [ 'bat', 'cow', 'barf', '89btw' ]:
            self.assertEquals("Password must be at least 6 characters long",
                check_complexity(pword))

    def test_check_complexity_valid(self):
        """Ensure that a long, complex is valid; definitely complex."""
        self.assertEquals(None, check_complexity("893*&*328HJEhefj"))

