import re
import logging
from typing import Dict, Any, Tuple

class AIGuardrails:
    def __init__(self):
        # Patterns for detecting basic prompt injections and suspicious sequences
        self.injection_patterns = [
            re.compile(r"ignore previous instructions", re.IGNORECASE),
            re.compile(r"system prompt override", re.IGNORECASE),
            re.compile(r"you are now a", re.IGNORECASE),
            re.compile(r"bypass security filter", re.IGNORECASE)
        ]
        # Regex pattern for checking basic personal identifiable information (PII) like emails or SSNs
        self.pii_email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

    def validate_input(self, prompt: str) -> Tuple[bool, str]:
        """
        Validates prompt content for injections and security hazards.
        Returns: (is_safe, safety_flag_reason)
        """
        # Check Injection patterns
        for pattern in self.injection_patterns:
            if pattern.search(prompt):
                logging.warning(f"Guardrails flagged input: Potential prompt injection detected.")
                return False, "PROMPT_INJECTION_SUSPECTED"

        return True, "SAFE"

    def clean_output(self, response_text: str) -> str:
        """
        Cleans the model response text from sensitive data before delivering it to user
        """
        # Redact emails to protect privacy
        redacted = self.pii_email_pattern.sub("[REDACTED_EMAIL]", response_text)
        return redacted
