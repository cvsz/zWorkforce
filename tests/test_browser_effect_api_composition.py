import unittest

from zworkforce.browser_effect_api import BrowserEffectApp
from zworkforce.workspace_grant_api import WorkspaceGrantApp


class BrowserEffectApiCompositionTests(unittest.TestCase):
    def test_browser_effect_app_extends_workspace_api_stack(self):
        self.assertTrue(issubclass(BrowserEffectApp, WorkspaceGrantApp))


if __name__ == "__main__":
    unittest.main()
