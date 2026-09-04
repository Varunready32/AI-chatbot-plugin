from __future__ import annotations

from contextvars import ContextVar
from typing import Any


current_table_context: ContextVar[dict[str, Any] | None] = ContextVar(
    "current_table_context",
    default=None,
)
