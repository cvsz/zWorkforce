from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any
import urllib.parse


class CitationValidationError(Exception):
    pass


@dataclass(frozen=True)
class Citation:
    url: str
    title: str
    published_date: str
    reliability_score: float
    excerpt: str
    metadata: dict[str, Any] = field(default_factory=dict)


class CitationValidator:
    """Validates structured citations for deep research results, enforces JSON Schema compliance,
    and filters out low-reliability sources below the default 0.65 threshold.
    """
    def __init__(self, min_reliability_threshold: float = 0.65):
        self.min_threshold = float(min_reliability_threshold)

    def validate_citation(self, data: dict[str, Any]) -> Citation:
        if not isinstance(data, dict):
            raise CitationValidationError("citation data must be a dictionary")

        # 1. URL validation
        url = str(data.get("url", "")).strip()
        if not url:
            raise CitationValidationError("field 'url' is required")
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise CitationValidationError(f"invalid citation URL format: {url!r}")

        # 2. Title validation
        title = str(data.get("title", "")).strip()
        if not title:
            raise CitationValidationError("field 'title' is required and cannot be empty")

        # 3. Published date validation
        published_date = str(data.get("published_date", "")).strip()
        if not published_date:
            raise CitationValidationError("field 'published_date' is required")

        # 4. Excerpt validation
        excerpt = str(data.get("excerpt", "")).strip()
        if not excerpt or len(excerpt) < 10:
            raise CitationValidationError("field 'excerpt' must contain at least 10 characters")

        # 5. Reliability score validation and threshold enforcement
        try:
            score = float(data.get("reliability_score", 0.0))
        except (ValueError, TypeError) as exc:
            raise CitationValidationError("field 'reliability_score' must be a numeric float") from exc

        if not (0.0 <= score <= 1.0):
            raise CitationValidationError(f"reliability_score must be between 0.0 and 1.0 (got {score})")

        if score < self.min_threshold:
            raise CitationValidationError(
                f"citation reliability score ({score:.2f}) is below minimum acceptable threshold ({self.min_threshold:.2f})"
            )

        metadata = dict(data.get("metadata", {}))
        return Citation(
            url=url,
            title=title,
            published_date=published_date,
            reliability_score=score,
            excerpt=excerpt,
            metadata=metadata,
        )

    def filter_and_rank_citations(self, raw_citations: list[dict[str, Any]]) -> list[Citation]:
        valid_citations: list[Citation] = []
        for raw in raw_citations:
            try:
                citation = self.validate_citation(raw)
                valid_citations.append(citation)
            except CitationValidationError:
                continue
        # Rank by reliability score descending
        return sorted(valid_citations, key=lambda c: c.reliability_score, reverse=True)
