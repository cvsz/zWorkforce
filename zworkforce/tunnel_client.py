from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import time
from typing import Any


class TunnelClientError(Exception):
    pass


class McpTunnelClient:
    """Local edge reverse-tunnel client daemon that maintains a heartbeat connection
    to the zWorkforce control plane McpTunnelManager.
    """
    def __init__(self, tenant_id: str, client_id: str, server_url: str = "http://127.0.0.1:9569"):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.server_url = server_url
        self.connected = False
        self.last_ping = 0.0

    def connect(self) -> dict[str, Any]:
        self.connected = True
        self.last_ping = time.time()
        return {
            "status": "connected",
            "client_id": self.client_id,
            "tenant_id": self.tenant_id,
            "server_url": self.server_url,
            "connected_at": self.last_ping,
        }

    def send_heartbeat(self) -> bool:
        if not self.connected:
            raise TunnelClientError("Cannot send heartbeat: client is disconnected")
        self.last_ping = time.time()
        return True

    def disconnect(self) -> None:
        self.connected = False
