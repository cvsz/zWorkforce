import time
import hashlib
from typing import Dict, Any, Optional

class AICache:
    def __init__(self, default_ttl_seconds: int = 300):
        self.default_ttl = default_ttl_seconds
        self.store: Dict[str, Dict[str, Any]] = {}

    def _hash_key(self, prompt_id: str, context: Dict[str, Any]) -> str:
        # Create a unique stable hash from prompt_id and context variables
        stable_context = str(sorted(context.items()))
        combined = f"{prompt_id}:{stable_context}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def get(self, prompt_id: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        key = self._hash_key(prompt_id, context)
        record = self.store.get(key)
        
        if not record:
            return None
            
        # Check TTL expiration
        if time.time() > record["expires_at"]:
            del self.store[key]
            return None
            
        return record["value"]

    def set(self, prompt_id: str, context: Dict[str, Any], value: Any, ttl: Optional[int] = None):
        key = self._hash_key(prompt_id, context)
        ttl = ttl if ttl is not None else self.default_ttl
        
        self.store[key] = {
            "value": value,
            "expires_at": time.time() + ttl
        }

    def clear(self):
        self.store.clear()
