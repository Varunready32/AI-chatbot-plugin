from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Literal

from ..database import get_connection

Metric = Literal["revenue", "gross_revenue", "profit", "loss", "orders", "quantity", "profit_margin", "avg_order_value"]
Dimension = Literal["none", "year", "month", "day", "city", "category", "product", "status", "period"]
SortDirection = Literal["asc", "desc"]

METRICS: dict[str, str] = {
    "revenue": "SUM(f.revenue)",
    "gross_revenue": "SUM(f.gross_revenue)",
    "profit": "SUM(f.profit)",
    "loss": "SUM(f.loss)",
    "orders": "COUNT(DISTINCT f.order_id)",
    "quantity": "SUM(f.quantity)",
    "profit_margin": "CASE WHEN SUM(f.revenue) = 0 THEN 0 ELSE (SUM(f.profit) / SUM(f.revenue)) * 100 END",
    "avg_order_value": "CASE WHEN COUNT(DISTINCT f.order_id) = 0 THEN 0 ELSE SUM(f.revenue) / COUNT(DISTINCT f.order_id) END",
}

DIMENSIONS: dict[str, str] = {
    "year": "f.year",
    "month": "TO_CHAR(DATE_TRUNC('month', f.order_date), 'YYYY-MM')",
    "day": "TO_CHAR(f.order_date, 'YYYY-MM-DD')",
    "city": "f.city",
    "category": "f.category",
    "product": "f.product",
    "status": "f.status",
}


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date,)):
        return value.isoformat()
    return value


def _normalize_rows(rows: list[dict]) -> list[dict]:
    return [{k: _json_value(v) for k, v in row.items()} for row in rows]


def _calculate_range(
    *,
    year: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    relative_days: int | None = None,
    relative_months: int | None = None,
) -> tuple[date | None, date | None]:
    today = date.today()
    if relative_days is not None:
        if not 1 <= relative_days <= 3650:
            raise ValueError("relative_days must be between 1 and 3650")
        return today - timedelta(days=relative_days), today
    if relative_months is not None:
        if not 1 <= relative_months <= 120:
            raise ValueError("relative_months must be between 1 and 120")
        # POC-safe approximation; SQL date_trunc is used for grouping.
        return today - timedelta(days=relative_months * 30), today
    if year is not None:
        return date(year, 1, 1), date(year, 12, 31)
    if start_date or end_date:
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else today
        return start, end
    return None, None


def query_analytics_data(
    *,
    metric: Metric,
    dimension: Dimension = "none",
    year: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    relative_days: int | None = None,
    relative_months: int | None = None,
    city: str | None = None,
    cities: list[str] | None = None,
    category: str | None = None,
    categories: list[str] | None = None,
    product: str | None = None,
    products: list[str] | None = None,
    sort: SortDirection = "desc",
    limit: int = 20,
    compare_previous_period: bool = False,
) -> dict:
    if metric not in METRICS:
        raise ValueError(f"Unsupported metric: {metric}")
    if dimension not in ["none", "period", *DIMENSIONS.keys()]:
        raise ValueError(f"Unsupported dimension: {dimension}")
    if sort not in ("asc", "desc"):
        raise ValueError("sort must be asc or desc")

    limit = max(1, min(limit, 100))
    range_start, range_end = _calculate_range(
        year=year,
        start_date=start_date,
        end_date=end_date,
        relative_days=relative_days,
        relative_months=relative_months,
    )

    if compare_previous_period:
        if not range_start or not range_end:
            raise ValueError("compare_previous_period requires a date range")
        span = (range_end - range_start).days + 1
        prev_end = range_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=span - 1)
        current = query_analytics_data(
            metric=metric, dimension="none", start_date=range_start.isoformat(), end_date=range_end.isoformat(),
            city=city, cities=cities, category=category, categories=categories, product=product, products=products,
            sort=sort, limit=1,
        )
        previous = query_analytics_data(
            metric=metric, dimension="none", start_date=prev_start.isoformat(), end_date=prev_end.isoformat(),
            city=city, cities=cities, category=category, categories=categories, product=product, products=products,
            sort=sort, limit=1,
        )
        current_value = current["data"][0]["value"] if current["data"] else 0
        previous_value = previous["data"][0]["value"] if previous["data"] else 0
        pct_change = None if previous_value == 0 else ((current_value - previous_value) / previous_value) * 100
        return {
            "metric": metric,
            "dimension": "period",
            "date_range": {"start": range_start.isoformat(), "end": range_end.isoformat()},
            "data": [
                {"label": "previous_period", "value": previous_value, "start": prev_start.isoformat(), "end": prev_end.isoformat()},
                {"label": "current_period", "value": current_value, "start": range_start.isoformat(), "end": range_end.isoformat()},
            ],
            "comparison": {"absolute_change": current_value - previous_value, "percent_change": pct_change},
        }

    where = ["f.status <> 'CANCELLED'"]
    params: list[Any] = []

    if range_start:
        where.append("f.order_date >= %s")
        params.append(range_start)
    if range_end:
        where.append("f.order_date <= %s")
        params.append(range_end)
    if city:
        where.append("LOWER(f.city) = LOWER(%s)")
        params.append(city)
    if cities:
        where.append("LOWER(f.city) = ANY(%s)")
        params.append([x.lower() for x in cities])
    if category:
        where.append("LOWER(f.category) = LOWER(%s)")
        params.append(category)
    if categories:
        where.append("LOWER(f.category) = ANY(%s)")
        params.append([x.lower() for x in categories])
    if product:
        where.append("LOWER(f.product) LIKE LOWER(%s)")
        params.append(f"%{product}%")
    if products:
        where.append("LOWER(f.product) = ANY(%s)")
        params.append([x.lower() for x in products])

    metric_expr = METRICS[metric]
    where_sql = " AND ".join(where)

    if dimension == "none":
        sql = f"SELECT {metric_expr} AS value FROM order_facts f WHERE {where_sql}"
    else:
        dim_expr = DIMENSIONS[dimension]
        # Time dimensions should always be chronological when explicitly requested.
        if dimension in ("year", "month", "day"):
            order_clause = "dimension ASC"
        else:
            order_clause = f"value {sort.upper()}"
        sql = f"""
            SELECT {dim_expr} AS dimension, {metric_expr} AS value
            FROM order_facts f
            WHERE {where_sql}
            GROUP BY {dim_expr}
            ORDER BY {order_clause}
            LIMIT %s
        """
        params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    rows = _normalize_rows(rows)
    if dimension == "none":
        data = [{"label": metric, "value": rows[0]["value"] if rows else 0}]
    else:
        data = [{"label": row["dimension"], "value": row["value"]} for row in rows]

    return {
        "metric": metric,
        "dimension": dimension,
        "date_range": {
            "start": range_start.isoformat() if range_start else None,
            "end": range_end.isoformat() if range_end else None,
        },
        "filters": {
            "city": city, "cities": cities, "category": category, "categories": categories,
            "product": product, "products": products,
        },
        "sort": sort,
        "limit": limit,
        "data": data,
    }


def dashboard_yearly(metric: Metric, year: int | None = None, category: str | None = None, city: str | None = None) -> list[dict]:
    if year:
        result = query_analytics_data(metric=metric, dimension="year", year=year, category=category, city=city, limit=10)
    else:
        result = query_analytics_data(metric=metric, dimension="year", start_date="2019-01-01", end_date="2025-12-31", category=category, city=city, limit=10)
    return result["data"]


def category_analysis(year: int | None = None, city: str | None = None) -> list[dict]:
    start, end = _calculate_range(year=year) if year else (date(2019,1,1), date(2025,12,31))
    sql = """
        SELECT f.category,
               COUNT(DISTINCT f.order_id) AS orders,
               SUM(f.revenue) AS revenue,
               SUM(f.gross_revenue) AS gross_revenue,
               SUM(f.profit) AS profit,
               SUM(f.loss) AS loss
        FROM order_facts f
        WHERE f.status <> 'CANCELLED' AND f.order_date BETWEEN %s AND %s
    """
    params: list[Any] = [start, end]
    if city:
        sql += " AND LOWER(f.city)=LOWER(%s)"
        params.append(city)
    sql += " GROUP BY f.category ORDER BY revenue DESC"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return _normalize_rows(cur.fetchall())


def city_analysis(year: int | None = None, category: str | None = None) -> list[dict]:
    start, end = _calculate_range(year=year) if year else (date(2019,1,1), date(2025,12,31))
    sql = """
        SELECT f.city,
               COUNT(DISTINCT f.order_id) AS orders,
               SUM(f.revenue) AS revenue,
               SUM(f.profit) AS profit,
               SUM(f.loss) AS loss
        FROM order_facts f
        WHERE f.status <> 'CANCELLED' AND f.order_date BETWEEN %s AND %s
    """
    params: list[Any] = [start, end]
    if category:
        sql += " AND LOWER(f.category)=LOWER(%s)"
        params.append(category)
    sql += " GROUP BY f.city ORDER BY revenue DESC"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return _normalize_rows(cur.fetchall())


def dashboard_table(metric: Metric, year: int | None = None, category: str | None = None, city: str | None = None) -> list[dict]:
    """Dashboard-specific yearly table with requested derived columns."""
    if metric not in {"revenue", "gross_revenue", "profit", "loss", "orders"}:
        raise ValueError("Unsupported dashboard metric")
    where = ["f.status <> 'CANCELLED'", "f.order_date BETWEEN %s AND %s"]
    params: list[Any] = [date(2019, 1, 1), date(2025, 12, 31)]
    if year:
        where.append("f.year = %s")
        params.append(year)
    if category:
        where.append("LOWER(f.category)=LOWER(%s)")
        params.append(category)
    if city:
        where.append("LOWER(f.city)=LOWER(%s)")
        params.append(city)
    where_sql = " AND ".join(where)

    if metric == "orders":
        value_expr = "COUNT(DISTINCT f.order_id)"
    else:
        value_expr = METRICS[metric]

    if metric == "revenue":
        sql = f"""
        WITH yearly AS (
          SELECT f.year, {value_expr} AS revenue
          FROM order_facts f WHERE {where_sql}
          GROUP BY f.year
        )
        SELECT year, revenue,
          CASE WHEN LAG(revenue) OVER (ORDER BY year) IS NULL OR LAG(revenue) OVER (ORDER BY year)=0 THEN NULL
               ELSE ((revenue - LAG(revenue) OVER (ORDER BY year)) / LAG(revenue) OVER (ORDER BY year)) * 100 END AS growth_pct
        FROM yearly ORDER BY year
        """
    elif metric == "profit":
        sql = f"""
        SELECT f.year, SUM(f.profit) AS profit,
          CASE WHEN SUM(f.revenue)=0 THEN 0 ELSE (SUM(f.profit)/SUM(f.revenue))*100 END AS profit_margin_pct
        FROM order_facts f WHERE {where_sql}
        GROUP BY f.year ORDER BY f.year
        """
    else:
        sql = f"""
        SELECT f.year, {value_expr} AS {metric}
        FROM order_facts f WHERE {where_sql}
        GROUP BY f.year ORDER BY f.year
        """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return _normalize_rows(cur.fetchall())


def category_analysis_filtered(year: int | None = None, city: str | None = None, category: str | None = None) -> list[dict]:
    rows = category_analysis(year, city)
    if category:
        rows = [r for r in rows if str(r.get("category", "")).lower() == category.lower()]
    return rows


def city_analysis_filtered(year: int | None = None, category: str | None = None, city: str | None = None) -> list[dict]:
    rows = city_analysis(year, category)
    if city:
        rows = [r for r in rows if str(r.get("city", "")).lower() == city.lower()]
    return rows
