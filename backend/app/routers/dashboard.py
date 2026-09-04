from fastapi import APIRouter, HTTPException, Query
from ..services.analytics import dashboard_table, category_analysis_filtered, city_analysis_filtered

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load analytics data") from exc


@router.get("/revenue")
def revenue(year: int | None = Query(None), category: str | None = None, city: str | None = None):
    return _safe(dashboard_table, "revenue", year, category, city)


@router.get("/gross-revenue")
def gross_revenue(year: int | None = Query(None), category: str | None = None, city: str | None = None):
    return _safe(dashboard_table, "gross_revenue", year, category, city)


@router.get("/profit")
def profit(year: int | None = Query(None), category: str | None = None, city: str | None = None):
    return _safe(dashboard_table, "profit", year, category, city)


@router.get("/loss")
def loss(year: int | None = Query(None), category: str | None = None, city: str | None = None):
    return _safe(dashboard_table, "loss", year, category, city)


@router.get("/orders")
def orders(year: int | None = Query(None), category: str | None = None, city: str | None = None):
    return _safe(dashboard_table, "orders", year, category, city)


@router.get("/categories")
def categories(year: int | None = Query(None), city: str | None = None, category: str | None = None):
    return _safe(category_analysis_filtered, year, city, category)


@router.get("/cities")
def cities(year: int | None = Query(None), category: str | None = None, city: str | None = None):
    return _safe(city_analysis_filtered, year, category, city)
