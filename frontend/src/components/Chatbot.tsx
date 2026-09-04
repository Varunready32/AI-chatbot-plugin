import { useEffect, useMemo, useState } from "react";
import { Bot, DatabaseZap, Send, X } from "lucide-react";
import { askAgent } from "../services/api";
import type { AgentResponse, AITableContext } from "../types";
import ChartRenderer from "./ChartRenderer";

export default function Chatbot({
  open,
  onClose,
  table,
}: {
  open: boolean;
  onClose: () => void;
  table: AITableContext | null;
}) {
  const sessionId = useMemo(() => crypto.randomUUID(), [table?.table_id]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; text: string; response?: AgentResponse }>>([]);

  useEffect(() => {
    setMessages([]);
    setInput("");
  }, [table?.table_id]);

  if (!open || !table) return null;

  const send = async () => {
    const message = input.trim();
    if (!message || loading) return;
    setMessages((m) => [...m, { role: "user", text: message }]);
    setInput("");
    setLoading(true);
    try {
      const response = await askAgent({ message, session_id: sessionId, table });
      setMessages((m) => [...m, { role: "assistant", text: response.answer, response }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: e instanceof Error ? e.message : "Something went wrong." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <aside className="chat-panel">
        <header className="chat-header">
          <div><Bot size={20} /> <strong>{table.table_name} · Ask AI</strong></div>
          <button className="icon-btn" onClick={onClose}><X size={20} /></button>
        </header>
        <div className="chat-context">
          <span><DatabaseZap size={15} /> Attached-table mode</span>
          <span>{table.rows.length} rows · {table.columns.length} columns</span>
          {Object.keys(table.filters ?? {}).length > 0 && <span>Host filters: {JSON.stringify(table.filters)}</span>}
        </div>
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="assistant-bubble">
              I will answer only from the data attached to <strong>{table.table_name}</strong>. Try “What is the highest value?”, “Top 3 by revenue”, or “Show this as a bar chart.”
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={m.role === "user" ? "user-bubble" : "assistant-bubble"}>
              <div>{m.text}</div>
              {m.response?.chart && <ChartRenderer chart={m.response.chart} />}
              {m.response?.type === "table" && m.response.data && (
                <div className="mini-table-wrap"><table className="mini-table"><tbody>
                  {m.response.data.map((row, idx) => (
                    <tr key={idx}>{Object.values(row).map((v, j) => <td key={j}>{String(v ?? "")}</td>)}</tr>
                  ))}
                </tbody></table></div>
              )}
            </div>
          ))}
          {loading && <div className="assistant-bubble">Analyzing the attached table rows…</div>}
        </div>
        <div className="chat-input-row">
          <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Ask about this table…" />
          <button className="primary-btn" onClick={send} disabled={loading}><Send size={17} /></button>
        </div>
      </aside>
    </div>
  );
}
