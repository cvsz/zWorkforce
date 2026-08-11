import os
import requests
from typing import Dict, Any

class GroqProvider:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.default_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set in environment variables.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": kwargs.get("model", self.default_model),
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.3)
        }

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        res_json = response.json()
        return res_json["choices"][0]["message"]["content"]
