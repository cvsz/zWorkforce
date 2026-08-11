import time
import logging
from typing import Dict, Any, List

class AIMetricsTracker:
    def __init__(self):
        self.latency_records: Dict[str, List[float]] = {}
        self.call_counts: Dict[str, int] = {}
        self.error_counts: Dict[str, int] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def record_call(self, provider: str, latency: float, success: bool = True):
        # Initialize metrics keys if empty
        if provider not in self.latency_records:
            self.latency_records[provider] = []
            self.call_counts[provider] = 0
            self.error_counts[provider] = 0

        self.call_counts[provider] += 1
        if success:
            self.latency_records[provider].append(latency)
        else:
            self.error_counts[provider] += 1

        logging.info(f"Metrics recorded for {provider}: success={success}, latency={latency:.3f}s")

    def record_cache(self, hit: bool):
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def get_average_latency(self, provider: str) -> float:
        records = self.latency_records.get(provider, [])
        if not records:
            return 0.0
        return sum(records) / len(records)

    def get_report(self) -> Dict[str, Any]:
        report = {
            "cache_hit_rate": 0.0,
            "providers": {}
        }
        total_cache = self.cache_hits + self.cache_misses
        if total_cache > 0:
            report["cache_hit_rate"] = self.cache_hits / total_cache

        for provider in self.call_counts:
            report["providers"][provider] = {
                "calls": self.call_counts[provider],
                "errors": self.error_counts[provider],
                "avg_latency": self.get_average_latency(provider)
            }
        return report
