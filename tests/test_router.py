import unittest

from zworkforce.router import (
    ModelRouter,
    ModelCapabilities,
    ModelMetadata,
    FREE_MODEL_SPECS,
)


class ModelRouterTests(unittest.TestCase):
    def setUp(self):
        self.router = ModelRouter()

    def test_default_catalog_initialization(self):
        self.assertIn("openrouter/free", self.router.catalog)
        self.assertIn("qwen/qwen-2.5-coder-32b-instruct:free", self.router.catalog)
        self.assertIn("deepseek/deepseek-r1:free", self.router.catalog)
        self.assertTrue(self.router.catalog["openrouter/free"].capabilities.is_free)

    def test_resolve_free_model_default(self):
        model = self.router.resolve_free_model()
        self.assertIsNotNone(model)
        self.assertTrue(self.router.catalog[model].capabilities.is_free)

    def test_resolve_free_model_with_reasoning(self):
        model = self.router.resolve_free_model(required_reasoning=True)
        self.assertIsNotNone(model)
        caps = self.router.catalog[model].capabilities
        self.assertTrue(caps.reasoning)
        self.assertTrue(caps.is_free)

    def test_resolve_free_model_with_vision(self):
        model = self.router.resolve_free_model(required_vision=True)
        self.assertIsNotNone(model)
        caps = self.router.catalog[model].capabilities
        self.assertTrue(caps.input_image)
        self.assertTrue(caps.is_free)

    def test_choose_includes_free_candidate(self):
        tier, rationale = self.router.choose("Please summarize this small text", prefer_free=True)
        self.assertEqual(tier, "luna")
        self.assertIn("free_candidate", rationale)
        self.assertTrue(rationale["free_first"])
        self.assertIsNotNone(rationale["free_candidate"])

    def test_choose_hard_task_includes_reasoning_free_candidate(self):
        tier, rationale = self.router.choose(
            "Perform deep threat model and security architecture analysis of this cryptographic protocol with Traceback and formal proof",
            default_tier="sol",
            mutating=True,
            tool_count=5,
            prefer_free=True,
        )
        self.assertEqual(tier, "sol")
        free_cand = rationale["free_candidate"]
        self.assertIsNotNone(free_cand)
        caps = self.router.catalog[free_cand].capabilities
        self.assertTrue(caps.reasoning)


if __name__ == "__main__":
    unittest.main()
