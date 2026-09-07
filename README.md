# Plug-and-Play Ask AI Table Analytics POC

This repository is based on the e-commerce dashboard, redesigned around the real enterprise goal: a reusable Ask AI component that can be embedded beside existing ecommerce/analytics tables across multiple client applications.

## Core idea

The sample dashboard still uses PostgreSQL to populate its normal UI tables. **Ask AI does not query PostgreSQL.** When a user clicks Ask AI beside a table, the host React application passes that table's schema, currently available rows, active host filters, and metadata to the reusable chatbot.

```text
Sample PostgreSQL -> Dashboard API -> React table
                                      |
                                      +-> Ask AI plugin
                                          receives table schema + rows
                                                |
                                          Microsoft Foundry Agent
                                                |
                                   analyze_current_table / chart_current_table
                                                |
                                      supplied rows only (no DB call)
```

This proves that the AI component can later be reused for revenue, demand, inventory, capacity, or any other forecast table regardless of the original data source.

## Important separation

- `backend/app/services/analytics.py` + PostgreSQL: sample application's existing dashboard/data layer.
- `backend/app/services/table_analytics.py`: generic in-memory analytics used by Ask AI.
- `backend/app/ai/tools.py`: generic Foundry tools that operate only on the currently attached table.
- `frontend/src/components/Chatbot.tsx`: reusable Ask AI UI.
- `frontend/src/types/index.ts`: portable `AITableContext` integration contract.

## Portable table contract

A host application sends:

```json
{
  "table_id": "revenue-forecast",
  "table_name": "Revenue Forecast",
  "description": "Monthly forecast revenue by city",
  "columns": [
    {"key": "city", "label": "City", "data_type": "string"},
    {"key": "forecast_revenue", "label": "Forecast Revenue", "data_type": "currency"}
  ],
  "rows": [
    {"city": "Mumbai", "forecast_revenue": 1250000},
    {"city": "Hyderabad", "forecast_revenue": 920000}
  ],
  "filters": {"year": 2027},
  "metadata": {"application": "Forecast App", "currency": "INR"}
}
```

The Foundry model sees the schema and context. The actual rows remain in backend request context and are accessed by tools. Numerical answers must use tools.

## Local setup

### 1. Start only PostgreSQL

```bash
docker compose up -d db
```

The first start seeds the sample e-commerce database.

### 2. Configure environment

```bash
cp .env.example .env
```

Set your real Foundry values in `.env`:

```dotenv
FOUNDRY_PROJECT_ENDPOINT=https://YOUR-RESOURCE.services.ai.azure.com/api/projects/YOUR-PROJECT
FOUNDRY_MODEL=YOUR_DEPLOYMENT_NAME
```

For local auth:

```bash
az login
```

### 3. Run FastAPI locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env .env
uvicorn app.main:app --reload --port 8000
```

Check:

```text
http://localhost:8000/health
http://localhost:8000/docs
```

### 4. Run React locally

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`.

## What to test

### Revenue table
- `Which year has the highest revenue?`
- `Compare 2024 and 2025.`
- `Show revenue by year as a line chart.`

### Category table
- `Top 5 categories by revenue.`
- `Which category has the most orders?`
- `Show category revenue as a pie chart.`

### City table
- `Top 3 cities by profit.`
- `Which city has the highest loss?`
- `Show city revenue as a bar chart.`

Watch the architecture: the dashboard rows came from PostgreSQL, but after the table is rendered, the Ask AI request contains those rows and the generic AI tools analyze that supplied dataset.
 

## Production evolution

Do not send huge tables (tens/hundreds of thousands of rows) through the browser/LLM request. The next phase should replace `rows` with a generic `DataAdapter`/dataset handle for large tables. The same Foundry intent layer can then call an application-owned analytics API (SQL Server, Snowflake, Databricks, REST, etc.) without changing the Ask AI UI contract.
