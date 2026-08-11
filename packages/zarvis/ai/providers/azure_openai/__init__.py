import os
import requests
from typing import Dict, Any

class AzureOpenAIProvider:
    def __init__(self):
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")  # e.g., https://my-resource.openai.azure.com
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        if not self.api_key or not self.endpoint:
            raise ValueError("AZURE_OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT is not set.")

        url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"

        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.3)
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        res_json = response.json()
        return res_json["choices"][0]["message"]["content"]
