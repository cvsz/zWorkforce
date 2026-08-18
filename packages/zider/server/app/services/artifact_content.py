from __future__ import annotations

import base64
import binascii
import hashlib
from pathlib import PurePath
from typing import Any

import httpx

from .zworkforce_bridge import ZWorkforceBridge, ZWorkforceBridgeError


class GovernedArtifactContentLoader:
    """Fetch tenant-scoped artifact bytes only through the authenticated control plane."""

    timeout_seconds = 8.0
    max_bytes = 8 * 1024 * 1024

    async def __call__(self, artifact_id: str) -> dict[str, Any]:
        value = str(artifact_id or "").strip()
        if not ZWorkforceBridge._TASK_ID.fullmatch(value):
            raise ZWorkforceBridgeError("browser upload artifact id is invalid", status_code=400)
        base_url = ZWorkforceBridge._base_url()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    f"{base_url}/api/v1/artifacts/{value}/content",
                    headers=ZWorkforceBridge._headers(),
                )
        except httpx.RequestError as exc:
            raise ZWorkforceBridgeError("zWorkforce control plane is unavailable") from exc
        ZWorkforceBridge._raise_for_status(response, "artifact content")
        payload = ZWorkforceBridge._decode_json(response, "artifact content")
        encoded = payload.get("content_base64")
        if not isinstance(encoded, str):
            raise ZWorkforceBridgeError("zWorkforce artifact content is malformed", status_code=502)
        max_encoded = ((self.max_bytes + 2) // 3) * 4
        if len(encoded) > max_encoded:
            raise ZWorkforceBridgeError("zWorkforce artifact content exceeds the configured bound", status_code=502)
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ZWorkforceBridgeError("zWorkforce artifact content is malformed", status_code=502) from exc
        size = int(payload.get("size_bytes") or -1)
        if size != len(data) or len(data) > self.max_bytes:
            raise ZWorkforceBridgeError("zWorkforce artifact content size is invalid", status_code=502)
        digest = str(payload.get("sha256") or "").lower()
        if len(digest) != 64 or hashlib.sha256(data).hexdigest() != digest:
            raise ZWorkforceBridgeError("zWorkforce artifact content integrity check failed", status_code=502)
        raw_name = str(payload.get("name") or "upload.bin")
        name = PurePath(raw_name.replace("\\", "/")).name[:255] or "upload.bin"
        content_type = str(payload.get("content_type") or "application/octet-stream")[:255]
        return {"name": name, "mime_type": content_type, "buffer": data, "sha256": digest}
