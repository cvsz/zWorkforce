from typing import Dict, Any

class AIRoutingRules:
    @staticmethod
    def determine_optimal_provider(prompt: str, preferred: str) -> str:
        """
        Dynamically changes provider based on prompt characteristics if preferred is not forced.
        """
        # Lowercase for robust matching
        prompt_lower = prompt.lower()
        
        # 1. Complex code / programming task detected -> route to highest tier models (Claude / OpenAI)
        coding_signals = ["write code", "implement", "fix bug", "refactor", "function", "class", "programming"]
        if any(sig in prompt_lower for sig in coding_signals):
            return "claude"

        # 2. Mathematical/Reasoning logic detected -> DeepSeek / OpenAI
        reasoning_signals = ["reason", "prove", "math", "solve equation", "calculate"]
        if any(sig in prompt_lower for sig in reasoning_signals):
            return "deepseek"

        # 3. Simple question / greeting -> Flash models (Gemini)
        if len(prompt.split()) < 8:
            return "gemini"

        # Else stick to user preferred provider
        return preferred
