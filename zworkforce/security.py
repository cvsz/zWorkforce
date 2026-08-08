from dataclasses import dataclass
import hashlib, hmac
ROLE_LEVEL = {"viewer": 1, "operator": 2, "admin": 3}
@dataclass(frozen=True)
class Principal:
    name: str
    role: str
class AuthManager:
    def __init__(self, keys):
        self._keys = [(hashlib.sha256(k.encode()).digest(), role, i) for i, (k, role) in enumerate(keys)]
    def authenticate(self, authorization, x_api_key):
        candidate = x_api_key or ""
        if authorization and authorization.lower().startswith("bearer "): candidate = authorization[7:].strip()
        if not candidate: return None
        digest = hashlib.sha256(candidate.encode()).digest()
        for known, role, idx in self._keys:
            if hmac.compare_digest(digest, known): return Principal(f"api-key-{idx+1}", role)
        return None
    @staticmethod
    def require(principal, role):
        return bool(principal and ROLE_LEVEL.get(principal.role, 0) >= ROLE_LEVEL[role])
