from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from agent_framework import tool
from pydantic import Field

from ..services.table_analytics import analyze_table
from .table_runtime import current_table_context

Aggregation = Literal["sum", "average", "min", "max", "count", "distinct_count"]


def _get_table() -> dict[str, Any]:
    table = current_table_context.get()
    if table is None:
        raise RuntimeError("No table context is attached to the current Ask AI request")
    return table


def _validate_columns(table: dict[str, Any], metric: str | None, dimension: str | None, filters: dict[str, Any] | None) -> None:
    allowed = {column["key"] for column in table["columns"]}
    if metric and metric not in allowed:
        raise ValueError(f"Unknown metric column '{metric}'. Available columns: {sorted(allowed)}")
    if dimension and dimension not in allowed:
        raise ValueError(f"Unknown dimension column '{dimension}'. Available columns: {sorted(allowed)}")
    if filters:
        unknown = set(filters) - allowed
        if unknown:
            raise ValueError(f"Unknown filter columns: {sorted(unknown)}. Available columns: {sorted(allowed)}")


@tool(approval_mode="never_require")
def analyze_current_table(
    metric: Annotated[str | None, Field(description="Column to aggregate. Use null only for row count.")] = None,
    dimension: Annotated[str | None, Field(description="Optional column used to group the result.")] = None,
    aggregation: Annotated[Aggregation, Field(description="Aggregation: sum, average, min, max, count, or distinct_count.")] = "sum",
    filters: Annotated[dict[str, Any] | None, Field(description="Optional exact-match filters using columns from the current table only. Values may be scalars or arrays.")] = None,
    sort: Annotated[Literal["asc", "desc"], Field(description="Sort grouped results by value.")] = "desc",
    limit: Annotated[int, Field(description="Maximum grouped rows to return; backend caps this at 100.")] = 20,
) -> str:
    """Analyze the table attached to this Ask AI instance. Never queries PostgreSQL or another external data source."""
    table = _get_table()
    _validate_columns(table, metric, dimension, filters)
    result = analyze_table(
        rows=table["rows"],
        metric=metric,
        dimension=dimension,
        filters=filters,
        aggregation=aggregation,
        sort=sort,
        limit=limit,
    )
    result["table_id"] = table["table_id"]
    result["table_name"] = table["table_name"]
    result["source"] = "attached_table_rows"
    return json.dumps(result, default=str)


@tool(approval_mode="never_require")
def chart_current_table(
    chart_type: Annotated[Literal["bar", "pie", "line"], Field(description="Requested chart type.")],
    metric: Annotated[str, Field(description="Numeric column displayed by the chart.")],
    dimension: Annotated[str, Field(description="Column used for chart labels/groups.")],
    title: Annotated[str, Field(description="Short chart title based on the user's request.")],
    aggregation: Annotated[Aggregation, Field(description="Aggregation to apply before charting.")] = "sum",
    filters: Annotated[dict[str, Any] | None, Field(description="Optional exact-match filters using current-table columns only.")] = None,
    sort: Annotated[Literal["asc", "desc"], Field(description="Sort chart values before returning them.")] = "desc",
    limit: Annotated[int, Field(description="Maximum chart points; backend caps this at 100.")] = 20,
) -> str:
    """Build chart-ready data strictly from the current table rows; the frontend draws the chart."""
    table = _get_table()
    _validate_columns(table, metric, dimension, filters)
    result = analyze_table(
        rows=table["rows"],
        metric=metric,
        dimension=dimension,
        filters=filters,
        aggregation=aggregation,
        sort=sort,
        limit=limit,
    )
    chart = {
        "type": chart_type,
        "title": title,
        "dimension": dimension,
        "metric": metric,
        "data": result["data"],
        "table_id": table["table_id"],
        "source": "attached_table_rows",
    }
    return json.dumps(chart, default=str)
