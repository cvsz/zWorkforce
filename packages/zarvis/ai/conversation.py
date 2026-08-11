"""AI Conversation / Chat History Management Module.

Provides :class:`AIConversationManager` for managing multi-turn chat
sessions with thread-safe message storage, token-budget–aware context
windows, and full session lifecycle operations.

All timestamps are stored in ISO 8601 format (UTC).
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AIConversationManager:
    """Manage multiple concurrent chat sessions with bounded history.

    Parameters
    ----------
    max_history:
        Maximum number of messages retained per session.  When the limit
        is reached the oldest non-system messages are evicted first.
    """

    def __init__(self, max_history: int = 100) -> None:
        if max_history < 1:
            raise ValueError("max_history must be >= 1")
        self._max_history = max_history
        self._sessions: OrderedDict[str, _Session] = OrderedDict()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(
        self,
        session_id: Optional[str] = None,
        system_prompt: str = "",
    ) -> str:
        """Create a new conversation session.

        Parameters
        ----------
        session_id:
            Optional caller-supplied identifier.  A UUID-4 is generated
            when *None*.
        system_prompt:
            An optional system-level instruction prepended to the
            conversation.

        Returns
        -------
        str
            The identifier of the newly created session.

        Raises
        ------
        ValueError
            If *session_id* already exists.
        """
        sid = session_id or uuid.uuid4().hex
        with self._lock:
            if sid in self._sessions:
                raise ValueError(f"Session '{sid}' already exists")
            session = _Session(sid=sid, max_history=self._max_history)
            if system_prompt:
                session.add_message("system", system_prompt)
            self._sessions[sid] = session
        logger.info("Created session %s", sid)
        return sid

    def clear_session(self, session_id: str) -> None:
        """Remove all messages from a session but keep the session alive."""
        with self._lock:
            session = self._get_session(session_id)
            session.clear()
        logger.info("Cleared session %s", session_id)

    def delete_session(self, session_id: str) -> None:
        """Delete a session and all associated data."""
        with self._lock:
            self._get_session(session_id)  # validate existence
            del self._sessions[session_id]
        logger.info("Deleted session %s", session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Return metadata for every active session.

        Each dict contains ``session_id``, ``created_at``,
        ``message_count``, and ``last_activity``.
        """
        with self._lock:
            return [s.metadata() for s in self._sessions.values()]

    # ------------------------------------------------------------------
    # Message operations
    # ------------------------------------------------------------------

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a message to the conversation.

        Parameters
        ----------
        session_id:
            Target session.
        role:
            One of ``"user"``, ``"assistant"``, or ``"system"``.
        content:
            The message text.
        metadata:
            Arbitrary key/value pairs attached to the message.

        Raises
        ------
        KeyError
            If *session_id* does not exist.
        ValueError
            If *role* is not a recognised value or *content* is empty.
        """
        _validate_role(role)
        if not content:
            raise ValueError("Message content must not be empty")
        with self._lock:
            session = self._get_session(session_id)
            session.add_message(role, content, metadata)
        logger.debug("Added %s message to session %s", role, session_id)

    def get_history(
        self,
        session_id: str,
        last_n: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return the conversation history for a session.

        Parameters
        ----------
        session_id:
            Target session.
        last_n:
            When provided, return only the *last_n* most recent messages.
        """
        with self._lock:
            session = self._get_session(session_id)
            messages = session.messages
            if last_n is not None:
                messages = messages[-last_n:]
            return [_msg_to_dict(m) for m in messages]

    def get_context_window(
        self,
        session_id: str,
        max_tokens: int = 4000,
    ) -> List[Dict[str, Any]]:
        """Return the most recent messages fitting a token budget.

        Token count is *estimated* as ``word_count * 1.33`` (a common
        heuristic for English / mixed-language text when a tokeniser is
        not available).

        System messages are always included first and their cost is
        deducted from the budget before user/assistant messages are
        considered (most-recent first).
        """
        if max_tokens < 1:
            raise ValueError("max_tokens must be >= 1")

        with self._lock:
            session = self._get_session(session_id)
            system_msgs: List[_Message] = []
            other_msgs: List[_Message] = []
            for msg in session.messages:
                if msg.role == "system":
                    system_msgs.append(msg)
                else:
                    other_msgs.append(msg)

            budget = max_tokens
            selected_system: List[_Message] = []
            for msg in system_msgs:
                cost = _estimate_tokens(msg.content)
                if cost <= budget:
                    selected_system.append(msg)
                    budget -= cost

            selected_other: List[_Message] = []
            for msg in reversed(other_msgs):
                cost = _estimate_tokens(msg.content)
                if cost <= budget:
                    selected_other.append(msg)
                    budget -= cost
                else:
                    break

            selected_other.reverse()
            result = selected_system + selected_other
            return [_msg_to_dict(m) for m in result]

    # ------------------------------------------------------------------
    # Summarisation & export
    # ------------------------------------------------------------------

    def summarize_history(self, session_id: str) -> str:
        """Create a compact plain-text summary of the conversation.

        The summary lists each turn with its role and a truncated
        content preview, useful for debugging or injecting as a
        recap into a new context window.
        """
        with self._lock:
            session = self._get_session(session_id)
            if not session.messages:
                return "(empty conversation)"
            lines: List[str] = [
                f"Conversation {session_id} — "
                f"{len(session.messages)} message(s)"
            ]
            for idx, msg in enumerate(session.messages, 1):
                preview = msg.content[:120]
                if len(msg.content) > 120:
                    preview += "…"
                lines.append(f"  [{idx}] {msg.role}: {preview}")
            return "\n".join(lines)

    def export_session(self, session_id: str) -> str:
        """Serialise the full session (messages + metadata) as JSON.

        Returns
        -------
        str
            A JSON string with ``session_id``, ``created_at``,
            ``messages``, and ``message_count`` keys.
        """
        with self._lock:
            session = self._get_session(session_id)
            payload: Dict[str, Any] = {
                **session.metadata(),
                "messages": [_msg_to_dict(m) for m in session.messages],
            }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_session(self, session_id: str) -> "_Session":
        """Retrieve a session or raise :class:`KeyError`."""
        try:
            return self._sessions[session_id]
        except KeyError:
            raise KeyError(f"Session '{session_id}' not found") from None


# ======================================================================
# Private helpers
# ======================================================================

_VALID_ROLES = frozenset({"user", "assistant", "system"})


def _validate_role(role: str) -> None:
    if role not in _VALID_ROLES:
        raise ValueError(
            f"Invalid role '{role}'. Must be one of {sorted(_VALID_ROLES)}"
        )


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ``ceil(word_count * 1.33)``."""
    word_count = len(text.split())
    return max(1, int(word_count * 1.33 + 0.5))


def _msg_to_dict(msg: "_Message") -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "role": msg.role,
        "content": msg.content,
        "timestamp": msg.timestamp,
    }
    if msg.metadata:
        result["metadata"] = msg.metadata
    return result


# ======================================================================
# Internal data structures
# ======================================================================


class _Message:
    """Immutable value object representing a single chat message."""

    __slots__ = ("role", "content", "timestamp", "metadata")

    def __init__(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.role = role
        self.content = content
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.metadata = metadata


class _Session:
    """Internal container for a single conversation session."""

    def __init__(self, sid: str, max_history: int) -> None:
        self.sid = sid
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.max_history = max_history
        self.messages: List[_Message] = []

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.messages.append(_Message(role, content, metadata))
        self._enforce_limit()

    def clear(self) -> None:
        self.messages.clear()

    def metadata(self) -> Dict[str, Any]:
        last_ts = self.messages[-1].timestamp if self.messages else None
        return {
            "session_id": self.sid,
            "created_at": self.created_at,
            "message_count": len(self.messages),
            "last_activity": last_ts,
        }

    def _enforce_limit(self) -> None:
        """Evict oldest non-system messages when over the limit."""
        while len(self.messages) > self.max_history:
            for idx, msg in enumerate(self.messages):
                if msg.role != "system":
                    self.messages.pop(idx)
                    break
            else:
                self.messages.pop(0)
