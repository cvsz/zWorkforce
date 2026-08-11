"""Token estimation and usage tracking module for the ZeaZ AI Platform.

Provides word-based token estimation, cost calculation using a pricing table
for major LLM providers, and cumulative session usage tracking.
"""

import logging
import re
import threading
from collections import defaultdict
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (USD) — input / output
# Updated periodically; override via environment or config for accuracy.
PRICING_TABLE: Dict[str, Dict[str, Dict[str, float]]] = {
    "claude": {
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "claude-4-sonnet": {"input": 3.00, "output": 15.00},
        "claude-4-opus": {"input": 15.00, "output": 75.00},
    },
    "openai": {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "o3": {"input": 10.00, "output": 40.00},
        "o3-mini": {"input": 1.10, "output": 4.40},
    },
    "gemini": {
        "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
        "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
        "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    },
    "deepseek": {
        "deepseek-chat": {"input": 0.27, "output": 1.10},
        "deepseek-reasoner": {"input": 0.55, "output": 2.19},
        "deepseek-coder": {"input": 0.14, "output": 0.28},
    },
}

# Regex patterns used to detect code-heavy content.
_CODE_PATTERN = re.compile(
    r"[{}\[\]();=<>]|def |class |import |function |const |let |var |return "
)


class AITokenCounter:
    """Estimates token counts, calculates costs, and tracks cumulative usage.

    All public methods are thread-safe.

    Example::

        counter = AITokenCounter()
        tokens = counter.estimate_tokens("Hello, world!")
        counter.track_usage("openai", "gpt-4o", input_tokens=120, output_tokens=55)
        summary = counter.get_usage_summary()
    """

    def __init__(self, pricing_table: Dict | None = None) -> None:
        """Initialise the counter with an optional custom pricing table.

        Args:
            pricing_table: Nested dict ``{provider: {model: {input, output}}}``
                with prices per 1 M tokens.  Falls back to the built-in
                ``PRICING_TABLE`` when *None*.
        """
        self._pricing: Dict[str, Dict[str, Dict[str, float]]] = (
            pricing_table if pricing_table is not None else PRICING_TABLE
        )
        self._lock = threading.Lock()
        # _usage[provider][model] -> {"input_tokens": int, "output_tokens": int, "requests": int}
        self._usage: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "requests": 0})
        )

    # ------------------------------------------------------------------
    # Estimation
    # ------------------------------------------------------------------

    def estimate_tokens(self, text: str) -> int:
        """Estimate the token count for *text* using a word-based heuristic.

        For predominantly English prose the ratio is roughly **1 word ≈ 1.33
        tokens** (i.e. 0.75 words per token).  Code-heavy content typically
        tokenises into more tokens per word, so a higher multiplier (1.5) is
        applied when code patterns are detected.

        Args:
            text: The input string to estimate.

        Returns:
            Estimated token count (always ≥ 0).
        """
        if not text:
            return 0

        words = text.split()
        word_count = len(words)

        if word_count == 0:
            # Whitespace-only input — count characters as a rough proxy.
            return max(1, len(text) // 4)

        multiplier = self._token_multiplier(text)
        estimated = int(word_count * multiplier)

        logger.debug(
            "estimate_tokens: words=%d multiplier=%.2f estimated=%d",
            word_count,
            multiplier,
            estimated,
        )
        return max(1, estimated)

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        provider: str,
        model: str,
    ) -> float:
        """Estimate the USD cost for a given number of tokens.

        Args:
            input_tokens: Number of input (prompt) tokens.
            output_tokens: Number of output (completion) tokens.
            provider: Provider key (e.g. ``"openai"``).
            model: Model key (e.g. ``"gpt-4o"``).

        Returns:
            Estimated cost in USD.  Returns ``0.0`` when the provider/model
            combination is not found in the pricing table (a warning is
            logged).
        """
        provider_lower = provider.lower()
        model_lower = model.lower()

        prices = self._pricing.get(provider_lower, {}).get(model_lower)
        if prices is None:
            logger.warning(
                "estimate_cost: no pricing data for provider=%r model=%r",
                provider,
                model,
            )
            return 0.0

        input_cost = (input_tokens / 1_000_000) * prices["input"]
        output_cost = (output_tokens / 1_000_000) * prices["output"]
        total = round(input_cost + output_cost, 8)

        logger.debug(
            "estimate_cost: provider=%s model=%s input=$%.6f output=$%.6f total=$%.6f",
            provider,
            model,
            input_cost,
            output_cost,
            total,
        )
        return total

    # ------------------------------------------------------------------
    # Tracking
    # ------------------------------------------------------------------

    def track_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Record token usage for a single request.

        Args:
            provider: Provider key.
            model: Model key.
            input_tokens: Prompt tokens consumed.
            output_tokens: Completion tokens consumed.
        """
        provider_lower = provider.lower()
        model_lower = model.lower()

        with self._lock:
            bucket = self._usage[provider_lower][model_lower]
            bucket["input_tokens"] += input_tokens
            bucket["output_tokens"] += output_tokens
            bucket["requests"] += 1

        logger.info(
            "track_usage: provider=%s model=%s input=%d output=%d",
            provider,
            model,
            input_tokens,
            output_tokens,
        )

    def get_usage_summary(self) -> Dict:
        """Return a summary of cumulative token usage and estimated costs.

        Returns:
            A dict with the structure::

                {
                    "total_input_tokens": int,
                    "total_output_tokens": int,
                    "total_tokens": int,
                    "total_cost_usd": float,
                    "total_requests": int,
                    "by_provider": {
                        "<provider>": {
                            "<model>": {
                                "input_tokens": int,
                                "output_tokens": int,
                                "requests": int,
                                "cost_usd": float,
                            }
                        }
                    },
                }
        """
        total_input = 0
        total_output = 0
        total_cost = 0.0
        total_requests = 0
        by_provider: Dict[str, Dict[str, Dict]] = {}

        with self._lock:
            for provider, models in self._usage.items():
                by_provider[provider] = {}
                for model, counters in models.items():
                    inp = counters["input_tokens"]
                    out = counters["output_tokens"]
                    reqs = counters["requests"]
                    cost = self.estimate_cost(inp, out, provider, model)

                    by_provider[provider][model] = {
                        "input_tokens": inp,
                        "output_tokens": out,
                        "requests": reqs,
                        "cost_usd": cost,
                    }

                    total_input += inp
                    total_output += out
                    total_cost += cost
                    total_requests += reqs

        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": round(total_cost, 8),
            "total_requests": total_requests,
            "by_provider": by_provider,
        }

    # ------------------------------------------------------------------
    # Limit checking
    # ------------------------------------------------------------------

    def check_token_limit(self, text: str, max_tokens: int) -> Tuple[bool, int]:
        """Check whether *text* fits within a token limit.

        Args:
            text: The text to check.
            max_tokens: Maximum allowed tokens.

        Returns:
            A tuple ``(within_limit, estimated_tokens)`` where
            *within_limit* is ``True`` when the estimated count does not
            exceed *max_tokens*.
        """
        estimated = self.estimate_tokens(text)
        within = estimated <= max_tokens

        logger.debug(
            "check_token_limit: estimated=%d max=%d within=%s",
            estimated,
            max_tokens,
            within,
        )
        return within, estimated

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _token_multiplier(text: str) -> float:
        """Return a tokens-per-word multiplier based on content type.

        Code-heavy text uses a higher multiplier because symbols and
        identifiers tend to split into more sub-word tokens.
        """
        sample = text[:2000]
        code_matches = len(_CODE_PATTERN.findall(sample))
        word_count = max(len(sample.split()), 1)
        code_ratio = code_matches / word_count

        if code_ratio > 0.3:
            return 1.8  # heavy code
        if code_ratio > 0.1:
            return 1.5  # mixed
        return 1.33  # mostly prose
