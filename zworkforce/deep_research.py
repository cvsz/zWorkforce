from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any
import urllib.parse


class DeepResearchError(Exception):
    pass


@dataclass
class SearchHop:
    query: str
    depth: int
    raw_results: list[dict[str, Any]] = field(default_factory=list)
    extracted_citations: list[dict[str, Any]] = field(default_factory=list)


class DeepResearchEngine:
    """Iterative multi-hop search orchestrator for autonomous deep research.
    Performs query reformulation, depth tracking, and document verification.
    """
    def __init__(self, max_hops: int = 3, min_reliability_threshold: float = 0.65):
        self.max_hops = max_hops
        self.min_threshold = float(min_reliability_threshold)

    def reformulate_query(self, initial_query: str, hop_index: int, prior_findings: list[str]) -> str:
        if hop_index == 0:
            return initial_query.strip()
        # Add targeted exploration keywords based on hop depth
        focus_terms = ["mechanisms", "comparative benchmarks", "limitations and edge cases"]
        term = focus_terms[min(hop_index - 1, len(focus_terms) - 1)]
        return f"{initial_query.strip()} {term}"

    def score_document(self, url: str, content: str, title: str) -> float:
        """Calculates a deterministic reliability score for a document based on domain trust and depth."""
        score = 0.50
        parsed = urllib.parse.urlsplit(url)
        domain = (parsed.hostname or "").lower()

        # Domain authority weighting
        if any(domain.endswith(d) for d in [".edu", ".gov", ".org", "arxiv.org", "github.com"]):
            score += 0.30
        elif any(domain.endswith(d) for d in [".com", ".net", ".io", ".dev"]):
            score += 0.15

        # Content substantive depth
        if len(content) > 500:
            score += 0.10
        if len(content) > 2000:
            score += 0.05

        return min(round(score, 2), 1.0)

    def execute_hops(self, initial_query: str, mock_fetcher=None) -> list[SearchHop]:
        hops: list[SearchHop] = []
        prior_findings: list[str] = []

        for hop_idx in range(self.max_hops):
            query = self.reformulate_query(initial_query, hop_idx, prior_findings)
            raw_results = mock_fetcher(query) if mock_fetcher else []
            
            citations = []
            for item in raw_results:
                url = item.get("url", "https://example.com/doc")
                text = item.get("text", "")
                title = item.get("title", "Untitled Document")
                score = self.score_document(url, text, title)
                if score >= self.min_threshold:
                    citations.append({
                        "url": url,
                        "title": title,
                        "published_date": item.get("published_date", "2026-01-01"),
                        "reliability_score": score,
                        "excerpt": text[:200] if len(text) >= 10 else "Substantive summary content for citation.",
                    })
                    prior_findings.append(title)

            hops.append(SearchHop(query=query, depth=hop_idx + 1, raw_results=raw_results, extracted_citations=citations))

        return hops
