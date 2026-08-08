import unittest
from zworkforce.router import ModelRouter
class RouterTests(unittest.TestCase):
    def setUp(self): self.r=ModelRouter()
    def test_light(self): self.assertEqual(self.r.choose("Summarize and format these labels","luna")[0],"luna")
    def test_complex(self): self.assertEqual(self.r.choose("Debug a distributed race condition and threat model "+"x"*5000,"terra",True)[0],"sol")
    def test_override(self): self.assertEqual(self.r.choose("anything",override="terra")[0],"terra")
    def test_escalation(self): self.assertEqual(self.r.escalate("luna"),"terra"); self.assertEqual(self.r.escalate("terra"),"sol"); self.assertIsNone(self.r.escalate("sol"))
