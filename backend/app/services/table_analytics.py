from __future__ import annotations

from collections import defaultdict
from numbers import Number
from typing import Any, Literal

Aggregation = Literal["sum", "average", "min", "max", "count", "distinct_count"]
SortDirection = Literal["asc", "desc"]


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return value.casefold()
    return value


def _matches_filters(row: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    """Apply only explicit AI-requested filters over columns present in the supplied table."""
    if not filters:
        return True

    for key, expected in filters.items():
        if key not in row:
            raise ValueError(f"Filter column '{key}' is not present in the supplied table rows")

        actual = row.get(key)
        if isinstance(expected, list):
            normalized_expected = {_normalize(item) for item in expected}
            if _normalize(actual) not in normalized_expected:
                return False
        elif _normalize(actual) != _normalize(expected):
            return False

    return True


def _numeric_values(rows: list[dict[str, Any]], metric: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(metric)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, Number):
            raise ValueError(f"Column '{metric}' contains a non-numeric value and cannot use numeric aggregation")
        values.append(float(value))
    return values


def _aggregate(rows: list[dict[str, Any]], metric: str | None, aggregation: Aggregation) -> float | int:
    if aggregation == "count":
        return len(rows) if metric is None else sum(1 for row in rows if row.get(metric) is not None)

    if aggregation == "distinct_count":
        if not metric:
            raise ValueError("distinct_count requires a metric column")
        return len({str(row.get(metric)) for row in rows if row.get(metric) is not None})

    if not metric:
        raise ValueError(f"{aggregation} requires a numeric metric column")

    values = _numeric_values(rows, metric)
    if not values:
        return 0

    if aggregation == "sum":
        return sum(values)
    if aggregation == "average":
        return sum(values) / len(values)
    if aggregation == "min":
        return min(values)
    if aggregation == "max":
        return max(values)

    raise ValueError(f"Unsupported aggregation: {aggregation}")


def analyze_table(
    *,
    rows: list[dict[str, Any]],
    metric: str | None,
    dimension: str | None = None,
    filters: dict[str, Any] | None = None,
    aggregation: Aggregation = "sum",
    sort: SortDirection = "desc",
    limit: int = 20,
) -> dict[str, Any]:
    """Analyze only the dataset attached to the current Ask AI instance."""
    if sort not in {"asc", "desc"}:
        raise ValueError("sort must be 'asc' or 'desc'")

    limit = max(1, min(limit, 100))
    filtered = [row for row in rows if _matches_filters(row, filters)]

    if dimension is None:
        value = _aggregate(filtered, metric, aggregation)
        return {
            "metric": metric,
            "dimension": None,
            "aggregation": aggregation,
            "row_count": len(filtered),
            "filters": filters or {},
            "data": [{"label": metric or "rows", "value": value}],
        }

    grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in filtered:
        label = row.get(dimension)
        if label is not None:
            grouped[label].append(row)

    data = [
        {"label": label, "value": _aggregate(group_rows, metric, aggregation)}
        for label, group_rows in grouped.items()
    ]

    data.sort(key=lambda item: item["value"], reverse=sort == "desc")
    data = data[:limit]

    return {
        "metric": metric,
        "dimension": dimension,
        "aggregation": aggregation,
        "row_count": len(filtered),
        "filters": filters or {},
        "sort": sort,
        "limit": limit,
        "data": data,
    }
