import os
import requests
from typing import Dict, Any

class HuggingFaceProvider:
    def __init__(self):
        self.api_key = os.getenv("HF_API_KEY", "")
        self.default_model = os.getenv("HF_MODEL", "meta-llama/Llama-3.1-8B-Instruct")

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        if not self.api_key:
            raise ValueError("HF_API_KEY is not set in environment variables.")

        model = kwargs.get("model", self.default_model)
        url = f"https://api-inference.huggingface.co/models/{model}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Hugging Face Chat Template style payload
        inputs = prompt
        if system_prompt:
            inputs = f"<|system|>\n{system_prompt}\n<|user|>\n{prompt}\n<|assistant|>\n"

        payload = {
            "inputs": inputs,
            "parameters": {
                "max_new_tokens": kwargs.get("max_tokens", 1024),
                "temperature": kwargs.get("temperature", 0.3)
            }
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        res_json = response.json()
        
        # Safe extraction
        try:
            if isinstance(res_json, list):
                return res_json[0].get("generated_text", "")
            return res_json.get("generated_text", str(res_json))
        except Exception as e:
            raise RuntimeError(f"Failed to parse HuggingFace response: {e}. Raw response: {res_json}")
