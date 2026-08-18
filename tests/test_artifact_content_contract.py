import unittest

from zworkforce.artifact_content_api import ArtifactContentApp
from zworkforce.browser_effect_api import BrowserEffectApp
from zworkforce.db import Database


class ArtifactContentContractTests(unittest.TestCase):
    def test_artifact_content_app_extends_browser_effect_api(self):
        self.assertTrue(issubclass(ArtifactContentApp, BrowserEffectApp))

    def test_database_exposes_tenant_scoped_artifact_lookup(self):
        self.assertTrue(callable(getattr(Database, "get_artifact", None)))


if __name__ == "__main__":
    unittest.main()
