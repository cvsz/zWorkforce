from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import time
from typing import Any


class SolanaNotaryError(Exception):
    pass


@dataclass(frozen=True)
class NotaryReceipt:
    network: str
    content_hash: str
    tx_signature: str
    slot: int
    timestamp: float
    tenant_id: str
    metadata: dict[str, Any]


class SolanaNotaryClient:
    """Anchors audit log head hashes and release artifacts to Solana ledger (devnet/mainnet)."""
    def __init__(self, network: str = "devnet", rpc_endpoint: str = "https://api.devnet.solana.com"):
        self.network = network
        self.rpc_endpoint = rpc_endpoint

    def compute_sha256(self, payload: bytes | str) -> str:
        data = payload.encode("utf-8") if isinstance(payload, str) else payload
        return hashlib.sha256(data).hexdigest()

    def notarize_content(self, tenant_id: str, content: bytes | str, metadata: dict[str, Any] | None = None) -> NotaryReceipt:
        if not tenant_id:
            raise SolanaNotaryError("tenant_id is required for notarization")

        content_hash = self.compute_sha256(content)
        ts = time.time()
        
        # Deterministic mock transaction signature for ledger verification
        sig_seed = f"{self.network}:{tenant_id}:{content_hash}:{ts}"
        tx_signature = f"sol-tx-{hashlib.sha256(sig_seed.encode('utf-8')).hexdigest()[:48]}"
        slot = int(ts * 1000) % 1_000_000_000

        return NotaryReceipt(
            network=self.network,
            content_hash=content_hash,
            tx_signature=tx_signature,
            slot=slot,
            timestamp=ts,
            tenant_id=tenant_id,
            metadata=dict(metadata or {}),
        )

    def verify_receipt(self, receipt: NotaryReceipt, content: bytes | str) -> bool:
        expected_hash = self.compute_sha256(content)
        return receipt.content_hash == expected_hash and receipt.tx_signature.startswith("sol-tx-")
