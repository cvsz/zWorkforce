import unittest

from zworkforce.db import Database


class BrowserEffectApiContractTests(unittest.TestCase):
    def test_database_exposes_browser_effect_lifecycle_methods(self):
        for name in (
            "begin_browser_effect",
            "get_browser_effect",
            "claim_browser_effect",
            "finish_browser_effect",
            "reconcile_browser_effect",
        ):
            self.assertTrue(callable(getattr(Database, name, None)), name)


if __name__ == "__main__":
    unittest.main()
