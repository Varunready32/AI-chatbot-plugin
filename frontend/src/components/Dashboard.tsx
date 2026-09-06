import { useEffect, useState } from "react";
import { PlugZap, Sparkles } from "lucide-react";
import { getDashboard } from "../services/api";
import type { AIDataType, AITableContext, Filters } from "../types";
import AnalyticsTable from "./AnalyticsTable";
import Chatbot from "./Chatbot";

const categories = ["", "Clothing", "Electronics", "Furniture", "Grocery", "Beauty", "Sports", "Books", "Home & Kitchen"];
const cities = ["", "Hyderabad", "Bengaluru", "Mumbai", "Delhi", "Chennai", "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Kochi"];

const sections = [
  ["Revenue Analysis", "revenue", "Yearly net revenue and year-over-year growth."],
  ["Gross Revenue", "gross-revenue", "Yearly gross revenue before discounts."],
  ["Profit Analysis", "profit", "Yearly profit and profit margin."],
  ["Loss Analysis", "loss", "Yearly loss values."],
  ["Orders", "orders", "Yearly distinct order counts."],
  ["Category Analysis", "categories", "Category-level orders and financial metrics."],
  ["City Analysis", "cities", "City-level orders and financial metrics."],
] as const;

function inferDataType(key: string, values: unknown[]): AIDataType {
  if (key.includes("pct") || key.includes("margin")) return "percentage";
  if (["revenue", "gross_revenue", "profit", "loss", "cost"].some((token) => key.includes(token))) return "currency";
  if (key.includes("date") || key.includes("month")) return "date";
  const sample = values.find((value) => value !== null && value !== undefined);
  if (typeof sample === "number") return "number";
  if (typeof sample === "boolean") return "boolean";
  return "string";
}

function buildTableContext(
  title: string,
  path: string,
  description: string,
  rows: Array<Record<string, unknown>>,
  filters: Filters,
): AITableContext {
  const keys = rows.length ? Object.keys(rows[0]) : [];
  return {
    table_id: `ecommerce-poc:${path}`,
    table_name: title,
    description,
    columns: keys.map((key) => ({
      key,
      label: key.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      data_type: inferDataType(key, rows.map((row) => row[key])),
    })),
    rows,
    filters: { ...filters },
    metadata: {
      application: "E-Commerce Sample Forecast/Analytics App",
      currency: "INR",
      source: "host application table rows",
    },
  };
}

export default function Dashboard() {
  const [filters, setFilters] = useState<Filters>({});
  const [data, setData] = useState<Record<string, Array<Record<string, unknown>>>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [chatTable, setChatTable] = useState<AITableContext | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    Promise.all(sections.map(async ([, path]) => [path, await getDashboard(path, filters)] as const))
      .then((pairs) => { if (!cancelled) setData(Object.fromEntries(pairs)); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "Unable to load dashboard"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [filters.year, filters.category, filters.city]);

  return (
    <main className="page">
      <header className="topbar">
        <div>
          <div className="eyebrow"><Sparkles size={16}/> Plug-and-Play </div>
          <h1>Table Analytics Assistant</h1>
          <p>The sample app gets its dashboard data from PostgreSQL. Ask AI receives the already-rendered table rows and analyzes only that attached dataset.</p>
        </div>
        <div className="architecture-pill"><PlugZap size={17}/> Plugin is data-source independent</div>
      </header>

      <section className="filters card">
        <label>Year<select value={filters.year ?? ""} onChange={(e) => setFilters({ ...filters, year: e.target.value ? Number(e.target.value) : undefined })}><option value="">All years</option>{[2019,2020,2021,2022,2023,2024,2025].map((y)=><option key={y}>{y}</option>)}</select></label>
        <label>Category<select value={filters.category ?? ""} onChange={(e) => setFilters({ ...filters, category: e.target.value || undefined })}>{categories.map((c)=><option key={c} value={c}>{c || "All categories"}</option>)}</select></label>
        <label>City<select value={filters.city ?? ""} onChange={(e) => setFilters({ ...filters, city: e.target.value || undefined })}>{cities.map((c)=><option key={c} value={c}>{c || "All cities"}</option>)}</select></label>
        <button className="secondary-btn" onClick={() => setFilters({})}>Reset</button>
      </section>

      {error && <div className="error-box">{error}</div>}

      <section className="kpis">
        {[
          ["Revenue", "revenue", "revenue"],
          ["Profit", "profit", "profit"],
          ["Orders", "orders", "orders"],
          ["Loss", "loss", "loss"],
        ].map(([label, path, key]) => {
          const rows = data[path] ?? [];
          const total = rows.reduce((sum, r) => sum + (typeof r[key] === "number" ? Number(r[key]) : 0), 0);
          return <div className="kpi card" key={label}><span>{label}</span><strong>{new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(total)}</strong><small>{filters.year ? String(filters.year) : "2019–2025"}</small></div>;
        })}
      </section>

      <div className="grid">
        {sections.map(([title, path, description]) => {
          const rows = data[path] ?? [];
          return (
            <AnalyticsTable
              key={path}
              title={title}
              rows={rows}
              loading={loading}
              onAskAI={() => setChatTable(buildTableContext(title, path, description, rows, filters))}
            />
          );
        })}
      </div>

      <Chatbot open={!!chatTable} onClose={() => setChatTable(null)} table={chatTable} />
    </main>
  );
}
