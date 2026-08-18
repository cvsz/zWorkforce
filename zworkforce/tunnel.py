from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from typing import Any, Callable
import uuid


class TunnelError(Exception):
    pass


DEFAULT_MAX_TUNNELS_PER_TENANT = 16


@dataclass
class TunnelConnection:
    tunnel_id: str
    tenant_id: str
    client_id: str
    connected_at: float
    last_heartbeat_at: float
    exposed_tools: list[dict[str, Any]] = field(default_factory=list)
    active: bool = True


class McpTunnelManager:
    """Manages encrypted reverse-tunnel connections for localhost edge MCP servers.

    The registry is deliberately process-local: tunnels are short-lived,
    heartbeat-fenced connections rather than durable control-plane state.
    Registration is bounded per tenant to prevent memory exhaustion, stale
    tunnels are reaped by :meth:`prune_stale`, and every lifecycle transition
    is forwarded to an optional audit callback so the operator can persist
    tunnel registration into the database audit log.
    """
    def __init__(
        self,
        heartbeat_timeout_seconds: float = 30.0,
        max_tunnels_per_tenant: int = DEFAULT_MAX_TUNNELS_PER_TENANT,
        audit: Callable[[str, str, dict[str, Any]], None] | None = None,
    ):
        self.heartbeat_timeout = float(heartbeat_timeout_seconds)
        self.max_tunnels_per_tenant = max(1, int(max_tunnels_per_tenant))
        self._audit = audit
        self._tunnels: dict[str, TunnelConnection] = {}

    def _emit_audit(self, tenant_id: str, action: str, details: dict[str, Any]) -> None:
        if self._audit is not None:
            self._audit(tenant_id, action, details)

    def register_tunnel(self, tenant_id: str, client_id: str, exposed_tools: list[dict[str, Any]] | None = None) -> TunnelConnection:
        if not tenant_id:
            raise TunnelError("tenant_id is required")
        if not client_id:
            raise TunnelError("client_id is required")

        now = time.time()
        active = [
            conn for conn in self._tunnels.values()
            if conn.tenant_id == tenant_id and conn.active and now - conn.last_heartbeat_at <= self.heartbeat_timeout
        ]
        if len(active) >= self.max_tunnels_per_tenant:
            raise TunnelError(f"tenant {tenant_id!r} exceeded the tunnel limit ({self.max_tunnels_per_tenant})")

        tunnel_id = f"tun-{uuid.uuid4().hex[:12]}"
        conn = TunnelConnection(
            tunnel_id=tunnel_id,
            tenant_id=tenant_id,
            client_id=client_id,
            connected_at=now,
            last_heartbeat_at=now,
            exposed_tools=exposed_tools or [],
            active=True,
        )
        self._tunnels[tunnel_id] = conn
        self._emit_audit(tenant_id, "tunnel.register", {
            "tunnel_id": tunnel_id,
            "client_id": client_id,
            "tools_count": len(conn.exposed_tools),
        })
        return conn

    def record_heartbeat(self, tunnel_id: str) -> None:
        conn = self._tunnels.get(tunnel_id)
        if not conn or not conn.active:
            raise TunnelError(f"tunnel {tunnel_id!r} is not active")
        conn.last_heartbeat_at = time.time()

    def get_tunnel(self, tenant_id: str, tunnel_id: str) -> TunnelConnection:
        conn = self._tunnels.get(tunnel_id)
        if not conn or conn.tenant_id != tenant_id or not conn.active:
            raise TunnelError(f"tunnel {tunnel_id!r} not found or expired")
        if time.time() - conn.last_heartbeat_at > self.heartbeat_timeout:
            conn.active = False
            self._tunnels.pop(tunnel_id, None)
            raise TunnelError(f"tunnel {tunnel_id!r} heartbeat timed out")
        return conn

    def list_active_tunnels(self, tenant_id: str) -> list[dict[str, Any]]:
        now = time.time()
        result = []
        for tunnel_id, conn in list(self._tunnels.items()):
            if conn.tenant_id == tenant_id and conn.active:
                if now - conn.last_heartbeat_at <= self.heartbeat_timeout:
                    result.append({
                        "tunnel_id": conn.tunnel_id,
                        "client_id": conn.client_id,
                        "connected_at": conn.connected_at,
                        "tools_count": len(conn.exposed_tools),
                    })
                else:
                    conn.active = False
                    self._tunnels.pop(tunnel_id, None)
        return result

    def close_tunnel(self, tenant_id: str, tunnel_id: str) -> bool:
        conn = self._tunnels.get(tunnel_id)
        if conn and conn.tenant_id == tenant_id:
            conn.active = False
            self._tunnels.pop(tunnel_id, None)
            self._emit_audit(tenant_id, "tunnel.close", {
                "tunnel_id": tunnel_id,
                "client_id": conn.client_id,
            })
            return True
        return False

    def prune_stale(self, *, now: float | None = None) -> dict[str, int]:
        """Reap expired tunnels and return reaped/remaining counts.

        Safe to call from the scheduler on a fixed interval: it only mutates
        connections whose heartbeat has already lapsed or that were closed.
        """
        current = time.time() if now is None else float(now)
        reaped = 0
        for tunnel_id, conn in list(self._tunnels.items()):
            if not conn.active or current - conn.last_heartbeat_at > self.heartbeat_timeout:
                conn.active = False
                self._tunnels.pop(tunnel_id, None)
                self._emit_audit(conn.tenant_id, "tunnel.prune", {
                    "tunnel_id": tunnel_id,
                    "client_id": conn.client_id,
                    "reason": "inactive" if not conn.active else "heartbeat_timeout",
                })
                reaped += 1
        return {"reaped": reaped, "remaining": len(self._tunnels)}
