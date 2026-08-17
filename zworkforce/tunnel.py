from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from typing import Any, Callable
import uuid


class TunnelError(Exception):
    pass


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
    """Manages encrypted reverse-tunnel connections for localhost edge MCP servers."""
    def __init__(self, heartbeat_timeout_seconds: float = 30.0):
        self.heartbeat_timeout = float(heartbeat_timeout_seconds)
        self._tunnels: dict[str, TunnelConnection] = {}

    def register_tunnel(self, tenant_id: str, client_id: str, exposed_tools: list[dict[str, Any]] | None = None) -> TunnelConnection:
        if not tenant_id:
            raise TunnelError("tenant_id is required")
        if not client_id:
            raise TunnelError("client_id is required")

        tunnel_id = f"tun-{uuid.uuid4().hex[:12]}"
        now = time.time()
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
            raise TunnelError(f"tunnel {tunnel_id!r} heartbeat timed out")
        return conn

    def list_active_tunnels(self, tenant_id: str) -> list[dict[str, Any]]:
        now = time.time()
        result = []
        for conn in self._tunnels.values():
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
        return result

    def close_tunnel(self, tenant_id: str, tunnel_id: str) -> bool:
        conn = self._tunnels.get(tunnel_id)
        if conn and conn.tenant_id == tenant_id:
            conn.active = False
            return True
        return False
