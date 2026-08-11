import os
import requests
from typing import Dict, Any

class OllamaProvider:
    def __init__(self):
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.default_model = os.getenv("OLLAMA_MODEL", "llama3")

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        url = f"{self.host}/api/chat"

        headers = {
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": kwargs.get("model", self.default_model),
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.3)
            }
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=45
        )
        response.raise_for_status()
        res_json = response.json()
        return res_json["message"]["content"]
