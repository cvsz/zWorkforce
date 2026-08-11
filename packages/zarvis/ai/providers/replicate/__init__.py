import os
import time
import requests
from typing import Dict, Any

class ReplicateProvider:
    def __init__(self):
        self.api_key = os.getenv("REPLICATE_API_TOKEN", "")
        self.default_model = os.getenv("REPLICATE_MODEL", "meta/meta-llama-3-70b-instruct")

    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        if not self.api_key:
            raise ValueError("REPLICATE_API_TOKEN is not set in environment variables.")

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

        # Step 1: Create prediction
        model = kwargs.get("model", self.default_model)
        payload = {
            "input": {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": kwargs.get("temperature", 0.3)
            }
        }

        # Replicate models are typically formatted as 'author/name:version'
        # e.g., 'meta/meta-llama-3-70b-instruct'
        create_url = "https://api.replicate.com/v1/predictions"
        # We find the version key or deployment target in kwargs if needed
        version = kwargs.get("version", "")
        if "/" in model and ":" not in model and not version:
            # Standalone API deployment wrapper style or default routing
            pass
            
        payload["version"] = version or "706b0050f035a1e97e85cc1115b4974c2fa023e1ca28cae54c7b8d43f0545f94" # Llama 3 70B default fallback hash

        response = requests.post(create_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        prediction = response.json()
        prediction_id = prediction["id"]
        poll_url = prediction["urls"]["get"]

        # Step 2: Poll for completion
        for _ in range(30):
            poll_resp = requests.get(poll_url, headers=headers, timeout=10)
            poll_resp.raise_for_status()
            res_json = poll_resp.json()
            status = res_json["status"]
            
            if status == "succeeded":
                # Replicate output is typically a list of strings (tokens)
                return "".join(res_json["output"])
            elif status in ["failed", "canceled"]:
                raise RuntimeError(f"Replicate prediction failed or was canceled: {res_json.get('error', '')}")
            
            time.sleep(1.5)
            
        raise TimeoutError("Replicate prediction timed out.")
