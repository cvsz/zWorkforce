import os
import requests
from typing import Dict, Any

class CloudflareAIProvider:
    def __init__(self):
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
        self.default_model = os.getenv("CLOUDFLARE_AI_MODEL", "@cf/meta/llama-3.1-8b-instruct")

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        if not self.account_id or not self.api_token:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN is not set.")

        model = kwargs.get("model", self.default_model)
        url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{model}"

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "messages": messages
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        res_json = response.json()
        return res_json["result"]["response"]
