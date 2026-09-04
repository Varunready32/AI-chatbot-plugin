from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class DashboardFilters(BaseModel):
    """Filters used only by the sample e-commerce dashboard."""

    year: int | None = Field(default=None, ge=2019, le=2025)
    category: str | None = None
    city: str | None = None


class TableColumn(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=150)
    data_type: Literal["string", "number", "date", "currency", "percentage", "boolean"]
    description: str | None = Field(default=None, max_length=500)


class TableMetadata(BaseModel):
    application: str | None = None
    currency: str | None = None
    timezone: str | None = None
    source: str | None = None


class TableContext(BaseModel):
    """Portable contract a host application passes to the Ask AI plugin."""

    table_id: str = Field(min_length=1, max_length=150)
    table_name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    columns: list[TableColumn] = Field(min_length=1, max_length=100)
    rows: list[dict[str, Any]] = Field(default_factory=list, max_length=5000)
    filters: dict[str, Any] = Field(default_factory=dict)
    metadata: TableMetadata | None = None

    @model_validator(mode="after")
    def validate_rows_against_schema(self):
        allowed = {column.key for column in self.columns}
        for index, row in enumerate(self.rows):
            unknown = set(row) - allowed
            if unknown:
                raise ValueError(
                    f"Row {index} contains columns not declared in the table schema: {sorted(unknown)}"
                )
        return self


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(min_length=1, max_length=200)
    table: TableContext


class ChartPayload(BaseModel):
    type: Literal["bar", "pie", "line"]
    title: str
    dimension: str
    metric: str
    data: list[dict]


class ChatResponse(BaseModel):
    type: Literal["text", "chart", "table"]
    answer: str
    data: list[dict] | None = None
    chart: ChartPayload | None = None
