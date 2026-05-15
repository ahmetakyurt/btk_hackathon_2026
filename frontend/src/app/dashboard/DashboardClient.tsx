"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { type DashboardSummary, type InsightsResponse } from "@/lib/api";
import InsightsCard from "@/components/InsightsCard";

const PLATFORM_COLORS: Record<string, string> = {
  trendyol: "#f97316",
  amazon: "#eab308",
  own_site: "#3b82f6",
};

const PLATFORM_LIGHT: Record<string, string> = {
  trendyol: "#fed7aa",
  amazon: "#fef08a",
  own_site: "#bfdbfe",
};

const DECISION_LABEL: Record<string, string> = {
  price_updated: "Fiyat Guncellendi",
  floor_hit: "Taban Fiyat",
  no_action: "Islem Yok",
  buybox: "Buybox",
};

const DECISION_COLOR: Record<string, string> = {
  price_updated: "text-green-600 bg-green-50 border-green-200",
  floor_hit: "text-orange-600 bg-orange-50 border-orange-200",
  no_action: "text-zinc-500 bg-zinc-50 border-zinc-200",
  buybox: "text-blue-600 bg-blue-50 border-blue-200",
};

function StatCard({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4">
      <p className="text-xs text-zinc-400">{label}</p>
      <p className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 mt-1">{value}</p>
      {detail && <p className="text-[11px] text-zinc-400 mt-0.5">{detail}</p>}
    </div>
  );
}

export default function DashboardClient({ data, insights }: { data: DashboardSummary | null; insights: InsightsResponse | null }) {
  if (!data) {
    return (
      <div className="p-8">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 mb-6">Dashboard</h1>
        <div className="rounded-xl border border-dashed border-zinc-300 dark:border-zinc-700 p-16 text-center">
          <p className="text-zinc-500 text-sm">Backend&apos;e baglanilamadi.</p>
        </div>
      </div>
    );
  }

  if (data.platforms.length === 0) {
    return (
      <div className="p-8">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 mb-6">Dashboard</h1>
        <div className="rounded-xl border border-dashed border-zinc-300 dark:border-zinc-700 p-16 text-center">
          <p className="text-zinc-500 text-sm">Henuz veri yok. Urun ekleyip fiyatlandirma calistirdiktan sonra burada analizler gorunecek.</p>
        </div>
      </div>
    );
  }

  const formatTry = (v: number) => `${v.toFixed(2)} ₺`;
  const formatPct = (v: number) => `${(v * 100).toFixed(0)}%`;

  const totalProfit = data.platforms.reduce((acc, p) => acc + p.total_profit, 0);
  const avgBuybox =
    data.platforms.length > 0
      ? data.platforms.reduce((acc, p) => acc + p.buybox_win_rate, 0) / data.platforms.length
      : 0;

  return (
    <div className="p-8">
      <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 mb-6">Dashboard</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <StatCard label="Toplam Urun" value={String(data.total_products)} />
        <StatCard label="Listelenen" value={String(data.total_listed)} detail={`${data.platforms.length} platform`} />
        <StatCard label="Toplam Kar" value={formatTry(totalProfit)} />
        <StatCard label="Ort. Buybox" value={formatPct(avgBuybox)} />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Profit bar chart — spans 2 cols */}
        <div className="lg:col-span-2 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-5">
          <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-4">Platform Bazinda Kar</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.platforms} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
              <XAxis dataKey="platform_name" tick={{ fontSize: 12, fill: "#71717a" }} />
              <YAxis tick={{ fontSize: 11, fill: "#a1a1aa" }} tickFormatter={formatTry} />
              <Tooltip
                formatter={(value: number, name: string) => {
                  if (name === "total_profit") return [formatTry(value), "Kar"];
                  if (name === "floor_hit_count") return [String(value), "Taban Fiyat"];
                  return [String(value), name];
                }}
                contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e4e4e7" }}
              />
              <Bar dataKey="total_profit" name="total_profit" radius={[4, 4, 0, 0]}>
                {data.platforms.map((p) => (
                  <Cell key={p.platform_code} fill={PLATFORM_COLORS[p.platform_code] ?? "#71717a"} />
                ))}
              </Bar>
              <Bar dataKey="floor_hit_count" name="floor_hit_count" radius={[4, 4, 0, 0]} fill="#fca5a5" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Buybox rate indicators — spans 1 col */}
        <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-5">
          <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-4">Buybox Kazanma</h2>
          <div className="flex flex-col gap-4">
            {data.platforms.map((p) => (
              <div key={p.platform_code}>
                <div className="flex justify-between items-baseline mb-1">
                  <span className="text-xs text-zinc-500">{p.platform_name}</span>
                  <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-50">
                    {formatPct(p.buybox_win_rate)}
                  </span>
                </div>
                <div className="w-full h-2 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(p.buybox_win_rate * 100, 100)}%`,
                      backgroundColor: PLATFORM_COLORS[p.platform_code] ?? "#71717a",
                    }}
                  />
                </div>
                <p className="text-[10px] text-zinc-400 mt-0.5">
                  {p.total_decisions} karar · {p.floor_hit_count} taban
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* AI Insights */}
      <div className="mb-6">
        <InsightsCard data={insights} />
      </div>

      {/* Recent decisions table */}
      <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden">
        <div className="px-5 py-3 border-b border-zinc-100 dark:border-zinc-800">
          <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Son Ajan Kararlari</h2>
        </div>
        {data.recent_decisions.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-xs text-zinc-400">Henuz karar kaydi yok.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-zinc-50 dark:bg-zinc-800 text-left">
              <tr>
                <th className="px-4 py-2.5 font-medium text-zinc-500 text-xs">Zaman</th>
                <th className="px-4 py-2.5 font-medium text-zinc-500 text-xs">Platform</th>
                <th className="px-4 py-2.5 font-medium text-zinc-500 text-xs">SKU</th>
                <th className="px-4 py-2.5 font-medium text-zinc-500 text-xs">Eski Fiyat</th>
                <th className="px-4 py-2.5 font-medium text-zinc-500 text-xs">Yeni Fiyat</th>
                <th className="px-4 py-2.5 font-medium text-zinc-500 text-xs">Karar</th>
                <th className="px-4 py-2.5 font-medium text-zinc-500 text-xs">Sure</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {data.recent_decisions.map((log) => (
                <tr key={log.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                  <td className="px-4 py-2.5 text-xs text-zinc-500 font-mono">
                    {log.created_at
                      ? new Date(log.created_at).toLocaleTimeString("tr-TR", {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })
                      : "—"}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle"
                      style={{
                        backgroundColor: PLATFORM_COLORS[log.platform_code ?? ""] ?? "#a1a1aa",
                      }}
                    />
                    <span className="text-xs text-zinc-700 dark:text-zinc-300">{log.platform_code}</span>
                  </td>
                  <td className="px-4 py-2.5 text-xs font-mono text-zinc-500">{log.sku ?? "—"}</td>
                  <td className="px-4 py-2.5 text-xs text-zinc-500">
                    {log.old_price != null ? `${Number(log.old_price).toFixed(2)} ₺` : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-xs font-medium text-zinc-800 dark:text-zinc-200">
                    {log.new_price != null ? `${Number(log.new_price).toFixed(2)} ₺` : "—"}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`text-xs font-medium px-2 py-0.5 rounded-full border ${DECISION_COLOR[log.decision] ?? "text-zinc-600 bg-zinc-50 border-zinc-200"}`}
                    >
                      {DECISION_LABEL[log.decision] ?? log.decision}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-zinc-400">
                    {log.duration_ms != null ? `${(log.duration_ms / 1000).toFixed(1)}s` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
