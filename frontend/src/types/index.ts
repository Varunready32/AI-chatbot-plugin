export type Filters = {
  year?: number;
  category?: string;
  city?: string;
};

export type AnalyticsRow = Record<string, string | number | boolean | null>;

export type AIDataType = "string" | "number" | "date" | "currency" | "percentage" | "boolean";

export type AITableColumn = {
  key: string;
  label: string;
  data_type: AIDataType;
  description?: string;
};

export type AITableContext = {
  table_id: string;
  table_name: string;
  description?: string;
  columns: AITableColumn[];
  rows: Array<Record<string, unknown>>;
  filters?: Record<string, unknown>;
  metadata?: {
    application?: string;
    currency?: string;
    timezone?: string;
    source?: string;
  };
};

export type ChartPayload = {
  type: "bar" | "pie" | "line";
  title: string;
  dimension: string;
  metric: string;
  data: Array<{ label: string | number; value: number }>;
};

export type AgentResponse = {
  type: "text" | "table" | "chart";
  answer: string;
  data?: Array<Record<string, unknown>> | null;
  chart?: ChartPayload | null;
};
