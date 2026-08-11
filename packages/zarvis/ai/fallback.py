import logging
from typing import List, Callable, Any, Dict

class AIFallbackManager:
    def __init__(self):
        # Default chain resolution order
        self.default_chain = ["claude", "openai", "gemini", "deepseek", "ollama"]

    def execute_with_fallback(self, provider_chain: List[str], execute_fn: Callable[[str], Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes the AI request using the chain of providers sequentially.
        If a provider fails, falls back to the next.
        """
        if not provider_chain:
            provider_chain = self.default_chain

        last_error = None
        for provider in provider_chain:
            try:
                logging.info(f"Attempting execution via provider: {provider}")
                result = execute_fn(provider)
                return result
            except Exception as e:
                logging.warning(f"Provider '{provider}' failed with error: {e}. Moving to next fallback.")
                last_error = e

        raise RuntimeError(f"All AI providers in fallback chain failed. Last error: {last_error}")
