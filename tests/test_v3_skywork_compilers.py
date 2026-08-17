from __future__ import annotations

import unittest

from zworkforce.deep_research import DeepResearchEngine, SearchHop
from zworkforce.document_compiler import DocumentCompiler


class DeepResearchEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = DeepResearchEngine(max_hops=2, min_reliability_threshold=0.65)

    def test_query_reformulation(self):
        q0 = self.engine.reformulate_query("Direct Preference Optimization", 0, [])
        self.assertEqual(q0, "Direct Preference Optimization")

        q1 = self.engine.reformulate_query("Direct Preference Optimization", 1, ["Doc 1"])
        self.assertIn("mechanisms", q1)

    def test_document_scoring(self):
        arxiv_score = self.engine.score_document("https://arxiv.org/abs/2305.18290", "a" * 600, "DPO Paper")
        self.assertGreaterEqual(arxiv_score, 0.80)

        random_score = self.engine.score_document("http://unknown-site.xyz/page", "short", "Random Page")
        self.assertLess(random_score, 0.65)

    def test_execute_hops(self):
        def mock_fetch(query):
            return [{
                "url": "https://arxiv.org/abs/test",
                "title": f"Paper on {query}",
                "text": "Detailed methodology and benchmark evaluation results for testing.",
                "published_date": "2026-01-15",
            }]

        hops = self.engine.execute_hops("AI Evaluation", mock_fetch)
        self.assertEqual(len(hops), 2)
        self.assertGreaterEqual(len(hops[0].extracted_citations), 1)


class DocumentCompilerTests(unittest.TestCase):
    def test_compile_marp_slides(self):
        sections = [{
            "heading": "Architecture",
            "content": "Overview of pipeline.",
            "citations": [{"title": "Source 1", "url": "https://example.com"}],
        }]
        marp = DocumentCompiler.compile_marp_slides("AI Research Report", sections)
        self.assertIn("marp: true", marp)
        self.assertIn("# AI Research Report", marp)
        self.assertIn("## Slide 1: Architecture", marp)

    def test_compile_tabular_csv(self):
        rows = [{"model": "Luna", "score": 95}, {"model": "Terra", "score": 88}]
        csv_out = DocumentCompiler.compile_tabular_csv(rows, ["model", "score"])
        self.assertIn("model,score", csv_out)
        self.assertIn("Luna,95", csv_out)

    def test_compile_ssml_audio_script(self):
        paragraphs = ["ยินดีต้อนรับสู่ระบบ Z.A.R.V.I.S.", "เริ่มการประมวลผลข้อมูล"]
        ssml = DocumentCompiler.compile_ssml_audio_script(paragraphs, "th-TH-Standard-A")
        self.assertIn("<speak>", ssml)
        self.assertIn('<voice name="th-TH-Standard-A">', ssml)
        self.assertIn("<s>ยินดีต้อนรับสู่ระบบ Z.A.R.V.I.S.</s>", ssml)


if __name__ == "__main__":
    unittest.main()
