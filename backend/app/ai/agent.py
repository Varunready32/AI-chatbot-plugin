from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential, ClientSecretCredential

from ..config import get_settings
from ..schemas import ChatRequest
from .prompts import SYSTEM_INSTRUCTIONS
from .table_runtime import current_table_context
from .tools import analyze_current_table, chart_current_table


@dataclass
class SessionState:
    table_id: str | None = None
    last_tool_args: dict[str, Any] | None = None
    last_tool_name: str | None = None
    last_answer: str | None = None
    history: list[dict[str, str]] = field(default_factory=list)


_sessions: dict[str, SessionState] = {}


def _credential():
    tenant = os.getenv("AZURE_TENANT_ID")
    client = os.getenv("AZURE_CLIENT_ID")
    secret = os.getenv("AZURE_CLIENT_SECRET")
    if tenant and client and secret:
        return ClientSecretCredential(tenant_id=tenant, client_id=client, client_secret=secret)
    return AzureCliCredential()


def _build_agent() -> Agent:
    settings = get_settings()
    if not settings.foundry_project_endpoint:
        raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT is missing")
    return Agent(
        client=FoundryChatClient(
            project_endpoint=settings.foundry_project_endpoint,
            model=settings.foundry_model,
            credential=_credential(),
        ),
        name="PortableTableAnalyticsAgent",
        instructions=SYSTEM_INSTRUCTIONS,
        tools=[analyze_current_table, chart_current_table],
        default_options={"store": False},
    )


def _json_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _extract_tool_activity(result) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None, dict[str, Any] | None]:
    """Version-tolerant extraction from Agent Framework message content."""
    table_payload = None
    chart_payload = None
    last_tool_name = None
    last_tool_args = None

    for message in getattr(result, "messages", []):
        for content in getattr(message, "contents", []):
            content_type = getattr(content, "type", None)

            if content_type == "function_call":
                last_tool_name = getattr(content, "name", None) or last_tool_name
                arguments = getattr(content, "arguments", None)
                parsed_args = _json_object(arguments)
                if parsed_args is not None:
                    last_tool_args = parsed_args

            elif content_type == "function_result":
                parsed = _json_object(getattr(content, "result", None))
                if not parsed:
                    continue
                if parsed.get("type") in {"bar", "pie", "line"} and isinstance(parsed.get("data"), list):
                    chart_payload = parsed
                elif isinstance(parsed.get("data"), list):
                    table_payload = parsed

    return table_payload, chart_payload, last_tool_name, last_tool_args


async def chat(request: ChatRequest) -> dict:
    state = _sessions.setdefault(request.session_id, SessionState())

    # A session reused for another table should not inherit the previous table's analytics context.
    if state.table_id and state.table_id != request.table.table_id:
        state = SessionState(table_id=request.table.table_id)
        _sessions[request.session_id] = state
    else:
        state.table_id = request.table.table_id

    table = request.table.model_dump()
    schema_context = {
        "table_id": request.table.table_id,
        "table_name": request.table.table_name,
        "description": request.table.description,
        "columns": [column.model_dump() for column in request.table.columns],
        "host_filters_already_reflected_in_rows": request.table.filters,
        "row_count_available_to_tools": len(request.table.rows),
        "metadata": request.table.metadata.model_dump(exclude_none=True) if request.table.metadata else {},
        "previous_tool": {
            "name": state.last_tool_name,
            "arguments": state.last_tool_args,
        },
        "recent_history": state.history[-4:],
    }

    prompt = (
        "Current Ask AI table context:\n"
        + json.dumps(schema_context, default=str)
        + "\n\nUser message:\n"
        + request.message
    )

    token = current_table_context.set(table)
    try:
        result = await _build_agent().run(prompt)
    finally:
        current_table_context.reset(token)

    answer = result.text
    tool_payload, chart_payload, tool_name, tool_args = _extract_tool_activity(result)

    if tool_name:
        state.last_tool_name = tool_name
    if tool_args:
        state.last_tool_args = tool_args
    state.last_answer = answer
    state.history.extend(
        [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": answer},
        ]
    )
    state.history = state.history[-10:]

    if chart_payload:
        return {
            "type": "chart",
            "answer": answer,
            "data": chart_payload.get("data"),
            "chart": chart_payload,
        }

    if tool_payload:
        data = tool_payload.get("data")
        return {
            "type": "table" if data and len(data) > 1 else "text",
            "answer": answer,
            "data": data,
            "chart": None,
        }

    return {"type": "text", "answer": answer, "data": None, "chart": None}
