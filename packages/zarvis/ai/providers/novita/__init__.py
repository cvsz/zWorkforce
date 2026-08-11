import os
import requests
from typing import Dict, Any

class NovitaProvider:
    def __init__(self):
        self.api_key = os.getenv("NOVITA_API_KEY", "")
        self.default_model = os.getenv("NOVITA_MODEL", "meta-llama/llama-3.1-70b-instruct")

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        if not self.api_key:
            raise ValueError("NOVITA_API_KEY is not set in environment variables.")

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
            "https://api.novita.ai/v3/openai/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        res_json = response.json()
        return res_json["choices"][0]["message"]["content"]
