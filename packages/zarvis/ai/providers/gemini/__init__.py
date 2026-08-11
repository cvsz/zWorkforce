import os
import requests
from typing import Dict, Any

class GeminiProvider:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.default_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables.")

        # Google Gemini REST API Chat Endpoint
        model = kwargs.get("model", self.default_model)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"

        headers = {
            "Content-Type": "application/json"
        }

        # Format prompt payload structure
        contents = [
            {
                "parts": [{"text": prompt}]
            }
        ]

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.3),
                "maxOutputTokens": kwargs.get("max_tokens", 4096)
            }
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        res_json = response.json()
        
        # Safe extraction of text response
        try:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Failed to parse Gemini API response: {e}. Response received: {res_json}")
