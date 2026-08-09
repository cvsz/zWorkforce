from __future__ import annotations

from dataclasses import dataclass
import json
import os
import time
import urllib.request
from typing import Any

from .security import Principal, ROLE_LEVEL, TENANT_RE


class IdentityError(RuntimeError):
    pass


@dataclass(frozen=True)
class OidcConfig:
    issuer: str
    audience: str
    tenant_claim: str = "tenant"
    role_claim: str = "role"
    scopes_claim: str = "scope"
    name_claim: str = "preferred_username"
    default_tenant: str = "default"
    default_role: str = "viewer"
    group_role_map: dict[str, str] | None = None


class OidcAuthenticator:
    def __init__(self, config: OidcConfig):
        self.config = config
        self._discovery_cache: dict[str, Any] | None = None
        self._discovery_at = 0.0
        self._jwk_clients: dict[str, Any] = {}

    def authenticate(self, token: str) -> Principal | None:
        try:
            import jwt
            from jwt import PyJWKClient
        except ImportError as exc:
            raise IdentityError("OIDC requires `pip install zworkforce[oidc]`") from exc
        try:
            discovery = self._discovery()
            jwks_uri = discovery["jwks_uri"]
            client = self._jwk_clients.get(jwks_uri)
            if client is None:
                client = PyJWKClient(jwks_uri, cache_keys=True, cache_jwk_set=True, lifespan=3600)
                self._jwk_clients[jwks_uri] = client
            signing_key = client.get_signing_key_from_jwt(token).key
            supported = discovery.get("id_token_signing_alg_values_supported") or ["RS256", "ES256"]
            algorithms = [a for a in supported if str(a).startswith(("RS", "PS", "ES")) or a == "EdDSA"]
            if not algorithms:
                return None
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=algorithms,
                audience=self.config.audience,
                issuer=self.config.issuer.rstrip("/"),
                options={"require": ["exp", "iat", "iss"]},
            )
        except Exception:
            return None
        tenant = str(claims.get(self.config.tenant_claim) or self.config.default_tenant).strip().lower()
        if not TENANT_RE.fullmatch(tenant):
            return None
        role = str(claims.get(self.config.role_claim) or "").lower()
        groups = claims.get("groups") or []
        if isinstance(groups, str):
            groups = [groups]
        for group in groups:
            mapped = (self.config.group_role_map or {}).get(str(group))
            if mapped and ROLE_LEVEL.get(mapped, 0) > ROLE_LEVEL.get(role, 0):
                role = mapped
        if role not in ROLE_LEVEL:
            role = self.config.default_role
        scopes_raw = claims.get(self.config.scopes_claim) or claims.get("scp") or "*"
        if isinstance(scopes_raw, str):
            scopes = tuple(x for x in scopes_raw.replace(",", " ").split() if x) or ("*",)
        elif isinstance(scopes_raw, list):
            scopes = tuple(str(x) for x in scopes_raw if str(x)) or ("*",)
        else:
            scopes = ("*",)
        name = str(claims.get(self.config.name_claim) or claims.get("email") or claims.get("sub") or "oidc-user")
        return Principal(name, role, tenant, scopes, "oidc:" + str(claims.get("sub") or name))

    def _discovery(self) -> dict[str, Any]:
        if self._discovery_cache is not None and time.monotonic() - self._discovery_at < 3600:
            return self._discovery_cache
        url = self.config.issuer.rstrip("/") + "/.well-known/openid-configuration"
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "zWorkforce-oidc/3"})
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read(1_048_576)
        data = json.loads(raw)
        if data.get("issuer", "").rstrip("/") != self.config.issuer.rstrip("/") or not data.get("jwks_uri"):
            raise IdentityError("invalid OIDC discovery document")
        self._discovery_cache = data
        self._discovery_at = time.monotonic()
        return data


def build_oidc_from_env(default_tenant: str) -> OidcAuthenticator | None:
    issuer = os.getenv("ZWORKFORCE_OIDC_ISSUER", "").strip()
    if not issuer:
        return None
    from urllib.parse import urlsplit
    parsed_issuer = urlsplit(issuer)
    if parsed_issuer.scheme not in {"https", "http"} or not parsed_issuer.hostname:
        raise IdentityError("ZWORKFORCE_OIDC_ISSUER must be an HTTP(S) URL")
    if parsed_issuer.scheme != "https" and parsed_issuer.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise IdentityError("remote OIDC issuers must use HTTPS")
    audience = os.getenv("ZWORKFORCE_OIDC_AUDIENCE", "").strip()
    if not audience:
        raise IdentityError("ZWORKFORCE_OIDC_AUDIENCE is required when OIDC is enabled")
    try:
        mapping = json.loads(os.getenv("ZWORKFORCE_OIDC_GROUP_ROLE_MAP", "{}"))
    except json.JSONDecodeError as exc:
        raise IdentityError("ZWORKFORCE_OIDC_GROUP_ROLE_MAP must be valid JSON") from exc
    if not isinstance(mapping, dict) or any(v not in ROLE_LEVEL for v in mapping.values()):
        raise IdentityError("OIDC group role map values must be viewer/operator/admin/superadmin")
    return OidcAuthenticator(OidcConfig(
        issuer=issuer,
        audience=audience,
        tenant_claim=os.getenv("ZWORKFORCE_OIDC_TENANT_CLAIM", "tenant"),
        role_claim=os.getenv("ZWORKFORCE_OIDC_ROLE_CLAIM", "role"),
        scopes_claim=os.getenv("ZWORKFORCE_OIDC_SCOPES_CLAIM", "scope"),
        name_claim=os.getenv("ZWORKFORCE_OIDC_NAME_CLAIM", "preferred_username"),
        default_tenant=os.getenv("ZWORKFORCE_OIDC_DEFAULT_TENANT", default_tenant),
        default_role=os.getenv("ZWORKFORCE_OIDC_DEFAULT_ROLE", "viewer"),
        group_role_map={str(k): str(v) for k, v in mapping.items()},
    ))
