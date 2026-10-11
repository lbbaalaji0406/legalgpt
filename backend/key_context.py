"""
SAULGPT — DYNAMIC API KEY CONTEXT (BYOK)
========================================
Thread-safe, async-safe context variable storage for per-request user API keys.
Allows clients to bring their own Groq API keys (BYOK) via HTTP headers,
preventing shared free-tier rate limits, while cleanly falling back to server .env.
"""

import contextvars
import os
from typing import Optional

# Holds the custom API key for the current request lifecycle
_current_groq_key: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_groq_key", default=None)


def set_request_groq_key(key: Optional[str]) -> None:
    """Set the API key for the current async request context."""
    if key and isinstance(key, str) and key.strip():
        _current_groq_key.set(key.strip())
    else:
        _current_groq_key.set(None)


def get_effective_groq_key() -> str:
    """
    Returns the user-supplied API key if present in the current request context;
    otherwise falls back to the server environment GROQ_API_KEY.
    """
    user_key = _current_groq_key.get()
    if user_key and isinstance(user_key, str) and user_key.strip():
        return user_key.strip()
    return os.getenv("GROQ_API_KEY", "").strip()


def has_user_custom_key() -> bool:
    """Returns True if the current request is powered by a client-provided key."""
    user_key = _current_groq_key.get()
    return bool(user_key and user_key.strip())
