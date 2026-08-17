from __future__ import annotations

import unittest

from zworkforce.citation_validator import CitationValidator, CitationValidationError
from zworkforce.a2a_discovery import A2ADiscoveryRegistry, AgentManifest, AgentCapability, A2ADiscoveryError


class CitationValidatorTests(unittest.TestCase):
    def setUp(self):
        self.validator = CitationValidator(min_reliability_threshold=0.65)

    def test_valid_citation_passes_validation(self):
        data = {
            "url": "https://arxiv.org/abs/2305.18290",
            "title": "Direct Preference Optimization",
            "published_date": "2023-05-29",
            "reliability_score": 0.95,
            "excerpt": "We propose Direct Preference Optimization (DPO), an algorithm for...",
            "metadata": {"doi": "10.48550/arXiv.2305.18290"},
        }
        citation = self.validator.validate_citation(data)
        self.assertEqual(citation.url, "https://arxiv.org/abs/2305.18290")
        self.assertEqual(citation.reliability_score, 0.95)

    def test_missing_fields_raise_error(self):
        with self.assertRaises(CitationValidationError) as ctx:
            self.validator.validate_citation({"title": "Test", "url": "https://example.com"})
        self.assertIn("field 'published_date' is required", str(ctx.exception))

    def test_low_reliability_score_rejected(self):
        data = {
            "url": "https://unverified-blog.example.com/post",
            "title": "Random Rumors",
            "published_date": "2026-01-01",
            "reliability_score": 0.45,
            "excerpt": "Some unverified rumors about new AI hardware benchmarks...",
        }
        with self.assertRaises(CitationValidationError) as ctx:
            self.validator.validate_citation(data)
        self.assertIn("is below minimum acceptable threshold", str(ctx.exception))

    def test_filter_and_rank_citations(self):
        raw_list = [
            {"url": "https://a.com", "title": "A", "published_date": "2026", "reliability_score": 0.70, "excerpt": "Valid excerpt A"},
            {"url": "https://b.com", "title": "B", "published_date": "2026", "reliability_score": 0.40, "excerpt": "Low score B"},
            {"url": "https://c.com", "title": "C", "published_date": "2026", "reliability_score": 0.92, "excerpt": "High score C"},
        ]
        ranked = self.validator.filter_and_rank_citations(raw_list)
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0].url, "https://c.com")
        self.assertEqual(ranked[1].url, "https://a.com")


class A2ADiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.registry = A2ADiscoveryRegistry()
        self.registry.register_agent(AgentManifest(
            agent_id="zeto-content",
            name="Zeto Publisher",
            department="marketing",
            description="Autonomous social media and shop publisher",
            capabilities=[
                AgentCapability("social_publish", "Publishes to social platforms", "1.0.0", tools=("social_publish", "shop_sync")),
            ]
        ))
        self.registry.register_agent(AgentManifest(
            agent_id="zarvis-voice",
            name="Zarvis Voice",
            department="assistant",
            description="Realtime voice streaming and PTT orchestrator",
            capabilities=[
                AgentCapability("voice_stream", "Streams PCM16 audio", "2.0.0", tools=("voice_session",)),
            ]
        ))

    def test_generate_well_known_manifest(self):
        manifest = self.registry.generate_well_known_manifest("https://workforce.zeaz.dev")
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(len(manifest["agents"]), 2)
        agent_ids = [a["agent_id"] for a in manifest["agents"]]
        self.assertIn("zeto-content", agent_ids)
        self.assertIn("zarvis-voice", agent_ids)

    def test_match_capable_agents(self):
        matched = self.registry.match_capable_agents("shop_sync")
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].agent_id, "zeto-content")

        matched_voice = self.registry.match_capable_agents("voice_session")
        self.assertEqual(len(matched_voice), 1)
        self.assertEqual(matched_voice[0].agent_id, "zarvis-voice")

        matched_none = self.registry.match_capable_agents("nonexistent_tool")
        self.assertEqual(len(matched_none), 0)


if __name__ == "__main__":
    unittest.main()
