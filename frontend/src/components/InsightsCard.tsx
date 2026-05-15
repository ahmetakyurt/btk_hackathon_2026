"use client";

import { type InsightsResponse } from "@/lib/api";

const ACTION_TYPE_LABEL: Record<string, string> = {
  pricing: "Fiyatlandırma",
  stock: "Stok",
  listing: "Listeleme",
  general: "Genel",
};

const ACTION_TYPE_COLOR: Record<string, string> = {
  pricing: "bg-blue-50 text-blue-700 border-blue-200",
  stock: "bg-orange-50 text-orange-700 border-orange-200",
  listing: "bg-purple-50 text-purple-700 border-purple-200",
  general: "bg-zinc-50 text-zinc-600 border-zinc-200",
};

const PLATFORM_COLORS: Record<string, string> = {
  trendyol: "#f97316",
  amazon: "#eab308",
  own_site: "#3b82f6",
};

const PRIORITY_COLOR = [
  "",
  "border-l-red-500",
  "border-l-orange-400",
  "border-l-yellow-400",
  "border-l-zinc-300",
  "border-l-zinc-200",
];

export default function InsightsCard({ data }: { data: InsightsResponse | null }) {
  if (!data || data.insights.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-5">
        <div className="flex items-center gap-2 mb-3">
          <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Bu Haftanın Önerileri</h2>
          <span className="text-xs text-zinc-400 bg-zinc-100 dark:bg-zinc-800 rounded-full px-2 py-0.5">AI</span>
        </div>
        <p className="text-xs text-zinc-400">Yeterli veri biriktiğinde öneriler burada görünecek.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Bu Haftanın Önerileri</h2>
          <span
            className={`text-xs rounded-full px-2 py-0.5 border ${
              data.is_ai_generated
                ? "bg-violet-50 text-violet-700 border-violet-200 dark:bg-violet-950/30 dark:text-violet-400 dark:border-violet-800"
                : "bg-zinc-100 text-zinc-500 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700"
            }`}
          >
            {data.is_ai_generated ? "✦ Gemini AI" : "Kural tabanlı"}
          </span>
        </div>
        <span className="text-[10px] text-zinc-400">
          {new Date(data.generated_at).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>

      <div className="flex flex-col gap-2">
        {data.insights.map((insight, i) => (
          <div
            key={i}
            className={`rounded-lg border border-l-4 border-zinc-100 dark:border-zinc-800 p-3 ${
              PRIORITY_COLOR[insight.priority] ?? "border-l-zinc-300"
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap mb-1">
                  <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 leading-tight">
                    {insight.title}
                  </span>
                  {insight.platform_code && (
                    <span
                      className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: PLATFORM_COLORS[insight.platform_code] ?? "#a1a1aa" }}
                      title={insight.platform_code}
                    />
                  )}
                </div>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-relaxed">
                  {insight.description}
                </p>
              </div>
              <span
                className={`text-[10px] font-medium px-1.5 py-0.5 rounded border flex-shrink-0 ${
                  ACTION_TYPE_COLOR[insight.action_type] ?? ACTION_TYPE_COLOR.general
                }`}
              >
                {ACTION_TYPE_LABEL[insight.action_type] ?? insight.action_type}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
