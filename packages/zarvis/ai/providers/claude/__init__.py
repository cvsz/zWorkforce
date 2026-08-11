import os
import requests
from typing import Dict, Any

class ClaudeProvider:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.default_model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest")

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set in environment variables.")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        # Safe parameter mappings
        payload = {
            "model": kwargs.get("model", self.default_model),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        res_json = response.json()
        return res_json["content"][0]["text"]
