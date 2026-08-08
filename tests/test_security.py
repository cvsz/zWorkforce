import unittest
from zworkforce.security import AuthManager
class SecurityTests(unittest.TestCase):
    def test_roles(self):
        a=AuthManager((("secret","operator"),)); p=a.authenticate("Bearer secret",None); self.assertTrue(a.require(p,"viewer")); self.assertTrue(a.require(p,"operator")); self.assertFalse(a.require(p,"admin")); self.assertIsNone(a.authenticate("Bearer wrong",None))
