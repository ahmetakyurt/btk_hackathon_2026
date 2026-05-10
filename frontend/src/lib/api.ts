const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type ApiOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options;
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status} ${res.statusText}: ${text}`);
  }

  return res.json() as Promise<T>;
}

// ─── Domain types ─────────────────────────────────────────────────────────────

export interface Platform {
  id: number;
  code: string;
  display_name: string;
  commission_rate: number;
  pricing_strategy: string;
  is_active: boolean;
}

export interface PlatformStatus {
  id: number;
  platform_code: string;
  platform_name: string;
  external_id: string | null;
  ai_generated_title: string | null;
  current_price: number | null;
  floor_price: number | null;
  has_buybox: boolean;
  status: "pending" | "listed" | "error";
}

export interface Product {
  id: number;
  sku: string;
  title: string;
  base_cost: number;
  shipping_cost: number;
  stock: number;
  category: string | null;
  created_at: string;
  platform_statuses: PlatformStatus[];
}

export interface ProductCreateRequest {
  sku: string;
  title: string;
  base_cost: number;
  shipping_cost: number;
  stock: number;
  category?: string;
  raw_specs?: Record<string, unknown>;
  initial_price?: number;
}

export interface PricingLog {
  id: number;
  product_platform_id: number;
  agent_name: string;
  trigger_event: string;
  sku: string | null;
  platform_code: string | null;
  old_price: number | null;
  new_price: number | null;
  decision: string;
  reasoning: string | null;
  tool_calls: ToolCallEntry[] | null;
  duration_ms: number | null;
  created_at: string;
}

export interface ToolCallEntry {
  tool: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
}

export interface CompetitorInfo {
  seller_name: string;
  price: number;
  has_buybox: boolean;
}

export interface PlatformSimState {
  product_platform_id: number;
  sku: string;
  product_title: string;
  platform_code: string;
  platform_name: string;
  external_id: string;
  own_price: number;
  own_has_buybox: boolean;
  competitors: CompetitorInfo[];
}

export const SSE_URL = `${API_BASE_URL}/api/agents/logs/stream`;
