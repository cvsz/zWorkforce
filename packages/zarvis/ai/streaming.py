"""Streaming response handler for AI providers.

Manages SSE-style streaming AI responses with per-stream buffering,
statistics tracking, and thread-safe operations.
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AIStreamHandler:
    """Manages streaming (SSE-style) AI responses with buffering and stats.

    Provides thread-safe operations for creating, pushing chunks to,
    finalizing, and aborting AI response streams. Each stream tracks
    chunk count, total characters, timing information, and status.

    Example::

        handler = AIStreamHandler()
        sid = handler.create_stream("req-001")
        handler.push_chunk(sid, "Hello")
        handler.push_chunk(sid, " world")
        result = handler.finalize(sid)
        # result["text"] == "Hello world"
    """

    _STATUS_ACTIVE = "active"
    _STATUS_COMPLETE = "complete"
    _STATUS_ABORTED = "aborted"

    def __init__(self) -> None:
        """Initialize the handler with an empty stream registry."""
        self._streams: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        logger.debug("AIStreamHandler initialized")

    def create_stream(self, stream_id: str) -> str:
        """Register a new stream and return its identifier.

        Args:
            stream_id: Unique identifier for the stream.

        Returns:
            The registered stream identifier.

        Raises:
            ValueError: If a stream with the given ID already exists.
        """
        with self._lock:
            if stream_id in self._streams:
                raise ValueError(
                    f"Stream '{stream_id}' already exists"
                )
            self._streams[stream_id] = {
                "buffer": [],
                "chunk_count": 0,
                "total_chars": 0,
                "start_time": time.monotonic(),
                "time_to_first_chunk": None,
                "status": self._STATUS_ACTIVE,
                "metadata": [],
                "abort_reason": None,
            }
            logger.info("Stream '%s' created", stream_id)
        return stream_id

    def push_chunk(
        self,
        stream_id: str,
        chunk: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Push a text chunk to the stream buffer.

        Args:
            stream_id: Identifier of the target stream.
            chunk: Text content to append.
            metadata: Optional metadata to associate with this chunk.

        Raises:
            KeyError: If the stream does not exist.
            RuntimeError: If the stream is not active.
        """
        with self._lock:
            stream = self._get_stream(stream_id)
            if stream["status"] != self._STATUS_ACTIVE:
                raise RuntimeError(
                    f"Cannot push to stream '{stream_id}' "
                    f"with status '{stream['status']}'"
                )
            if stream["time_to_first_chunk"] is None:
                stream["time_to_first_chunk"] = (
                    time.monotonic() - stream["start_time"]
                )
            stream["buffer"].append(chunk)
            stream["chunk_count"] += 1
            stream["total_chars"] += len(chunk)
            if metadata is not None:
                stream["metadata"].append(metadata)
            logger.debug(
                "Stream '%s': chunk #%d pushed (%d chars)",
                stream_id,
                stream["chunk_count"],
                len(chunk),
            )

    def get_buffer(self, stream_id: str) -> str:
        """Get the accumulated text for a stream.

        Args:
            stream_id: Identifier of the target stream.

        Returns:
            The concatenated text of all chunks pushed so far.

        Raises:
            KeyError: If the stream does not exist.
        """
        with self._lock:
            stream = self._get_stream(stream_id)
            return "".join(stream["buffer"])

    def finalize(self, stream_id: str) -> Dict[str, Any]:
        """Mark a stream as complete and return the full response with stats.

        Args:
            stream_id: Identifier of the target stream.

        Returns:
            A dictionary containing the full text, chunk count,
            total characters, elapsed time, time to first chunk,
            status, and collected metadata.

        Raises:
            KeyError: If the stream does not exist.
            RuntimeError: If the stream is not active.
        """
        with self._lock:
            stream = self._get_stream(stream_id)
            if stream["status"] != self._STATUS_ACTIVE:
                raise RuntimeError(
                    f"Cannot finalize stream '{stream_id}' "
                    f"with status '{stream['status']}'"
                )
            stream["status"] = self._STATUS_COMPLETE
            elapsed = time.monotonic() - stream["start_time"]
            result: Dict[str, Any] = {
                "stream_id": stream_id,
                "text": "".join(stream["buffer"]),
                "chunk_count": stream["chunk_count"],
                "total_chars": stream["total_chars"],
                "elapsed_seconds": round(elapsed, 4),
                "time_to_first_chunk": (
                    round(stream["time_to_first_chunk"], 4)
                    if stream["time_to_first_chunk"] is not None
                    else None
                ),
                "status": self._STATUS_COMPLETE,
                "metadata": stream["metadata"],
            }
            logger.info(
                "Stream '%s' finalized: %d chunks, %d chars, %.4fs",
                stream_id,
                stream["chunk_count"],
                stream["total_chars"],
                elapsed,
            )
            return result

    def is_active(self, stream_id: str) -> bool:
        """Check whether a stream is still active.

        Args:
            stream_id: Identifier of the target stream.

        Returns:
            ``True`` if the stream exists and has active status.
        """
        with self._lock:
            stream = self._streams.get(stream_id)
            if stream is None:
                return False
            return stream["status"] == self._STATUS_ACTIVE

    def abort(self, stream_id: str, reason: str) -> None:
        """Abort an active stream.

        Args:
            stream_id: Identifier of the target stream.
            reason: Human-readable reason for aborting.

        Raises:
            KeyError: If the stream does not exist.
            RuntimeError: If the stream is not active.
        """
        with self._lock:
            stream = self._get_stream(stream_id)
            if stream["status"] != self._STATUS_ACTIVE:
                raise RuntimeError(
                    f"Cannot abort stream '{stream_id}' "
                    f"with status '{stream['status']}'"
                )
            stream["status"] = self._STATUS_ABORTED
            stream["abort_reason"] = reason
            logger.warning(
                "Stream '%s' aborted: %s", stream_id, reason
            )

    def list_active_streams(self) -> List[str]:
        """List identifiers of all currently active streams.

        Returns:
            A list of stream IDs with active status.
        """
        with self._lock:
            return [
                sid
                for sid, data in self._streams.items()
                if data["status"] == self._STATUS_ACTIVE
            ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_stream(self, stream_id: str) -> Dict[str, Any]:
        """Retrieve a stream record or raise ``KeyError``.

        Must be called while ``self._lock`` is held.
        """
        try:
            return self._streams[stream_id]
        except KeyError:
            raise KeyError(
                f"Stream '{stream_id}' not found"
            ) from None
