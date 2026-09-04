import { Bot } from "lucide-react";

export default function AnalyticsTable({
  title,
  rows,
  loading,
  onAskAI,
}: {
  title: string;
  rows: Array<Record<string, unknown>>;
  loading: boolean;
  onAskAI: () => void;
}) {
  const columns = rows.length ? Object.keys(rows[0]) : [];
  return (
    <section className="card table-card">
      <div className="card-header">
        <div>
          <h3>{title}</h3>
          <small className="table-source-note">Ask AI analyzes the rows attached to this table</small>
        </div>
        <button className="ai-btn" onClick={onAskAI} disabled={loading || rows.length === 0}>
          <Bot size={17} /> Ask AI
        </button>
      </div>
      {loading ? <div className="empty">Loading…</div> : rows.length === 0 ? <div className="empty">No matching data.</div> : (
        <div className="table-scroll"><table>
          <thead><tr>{columns.map((c) => <th key={c}>{c.replaceAll("_", " ")}</th>)}</tr></thead>
          <tbody>{rows.map((row, i) => <tr key={i}>{columns.map((c) => <td key={c}>{format(row[c])}</td>)}</tr>)}</tbody>
        </table></div>
      )}
    </section>
  );
}

function format(v: unknown) {
  if (typeof v === "number") return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(v);
  return String(v ?? "");
}
