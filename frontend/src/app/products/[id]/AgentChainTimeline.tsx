import type { PlatformStatus, PricingLog } from "@/lib/api";

const TRIGGER_LABEL: Record<string, string> = {
  manual: "Manuel Tetikleme",
  competitor_price_change: "Rakip Fiyat Değişimi",
  scheduled: "Zamanlanmış",
};

const DECISION_BADGE: Record<string, { label: string; cls: string }> = {
  price_updated: { label: "Fiyat Güncellendi", cls: "text-green-700 bg-green-50 border-green-200" },
  floor_hit: { label: "Floor Hit", cls: "text-yellow-700 bg-yellow-50 border-yellow-200" },
  no_action: { label: "İşlem Yok", cls: "text-zinc-500 bg-zinc-50 border-zinc-200" },
  pending_approval: { label: "Onay Bekliyor", cls: "text-orange-700 bg-orange-50 border-orange-200" },
};

const PLATFORM_COLOR: Record<string, string> = {
  trendyol: "bg-orange-500",
  amazon: "bg-yellow-400",
  own_site: "bg-blue-500",
};

const AGENT_ICON: Record<string, string> = {
  ListingAgent: "📝",
  PricingAgent: "💹",
  CompetitorWatcher: "👁",
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("tr-TR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return "—";
  }
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
    });
  } catch {
    return "";
  }
}

interface AgentChainTimelineProps {
  platformStatuses: PlatformStatus[];
  logsMap: Map<number, PricingLog[]>;
  productCreatedAt: string;
}

export function AgentChainTimeline({
  platformStatuses,
  logsMap,
  productCreatedAt,
}: AgentChainTimelineProps) {
  // Build flat timeline entries from all logs
  type Entry =
    | { kind: "listing"; time: string; platforms: PlatformStatus[] }
    | { kind: "pricing"; time: string; log: PricingLog; platformCode: string; platformName: string };

  const entries: Entry[] = [];

  // Listing entry — one per listed platform grouped together
  const listedStatuses = platformStatuses.filter((ps) => ps.status === "listed");
  if (listedStatuses.length > 0) {
    entries.push({ kind: "listing", time: productCreatedAt, platforms: listedStatuses });
  }

  // Pricing log entries — all platforms merged and sorted desc
  for (const ps of platformStatuses) {
    const logs = logsMap.get(ps.id) ?? [];
    for (const log of logs) {
      entries.push({
        kind: "pricing",
        time: log.created_at,
        log,
        platformCode: ps.platform_code,
        platformName: ps.platform_name,
      });
    }
  }

  // Sort descending (newest first)
  entries.sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());

  if (entries.length === 0) return null;

  return (
    <div className="mt-8">
      <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-4">
        Agent Karar Zinciri
      </h2>
      <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden">
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-[2.375rem] top-0 bottom-0 w-px bg-zinc-100 dark:bg-zinc-800" />

          <div className="flex flex-col">
            {entries.map((entry, i) => {
              if (entry.kind === "listing") {
                return (
                  <div key={`listing-${i}`} className="flex gap-4 px-5 py-4">
                    {/* Timeline dot */}
                    <div className="shrink-0 flex flex-col items-center">
                      <div className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 border-2 border-blue-400 flex items-center justify-center z-10">
                        <span className="text-[8px]">📝</span>
                      </div>
                    </div>
                    {/* Content */}
                    <div className="flex-1 min-w-0 pb-4">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                          ListingAgent
                        </span>
                        <span className="text-[10px] text-zinc-400">
                          {formatDate(entry.time)} {formatTime(entry.time)}
                        </span>
                      </div>
                      <p className="text-[11px] text-zinc-500 mb-2">
                        Gemini ile platform başlıkları ve açıklamaları üretildi, listeleme tamamlandı.
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {entry.platforms.map((ps) => (
                          <span
                            key={ps.platform_code}
                            className="flex items-center gap-1 text-[10px] text-zinc-600 dark:text-zinc-400 bg-zinc-100 dark:bg-zinc-800 rounded-full px-2 py-0.5"
                          >
                            <span
                              className={`w-1.5 h-1.5 rounded-full ${PLATFORM_COLOR[ps.platform_code] ?? "bg-zinc-400"}`}
                            />
                            {ps.platform_name}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              }

              // pricing entry
              const { log, platformCode, platformName } = entry;
              const trigger = TRIGGER_LABEL[log.trigger_event] ?? log.trigger_event;
              const decision = DECISION_BADGE[log.decision];
              const dotColor =
                log.decision === "price_updated"
                  ? "border-green-400 bg-green-50 dark:bg-green-900/40"
                  : log.decision === "floor_hit"
                  ? "border-yellow-400 bg-yellow-50 dark:bg-yellow-900/40"
                  : log.decision === "pending_approval"
                  ? "border-orange-400 bg-orange-50 dark:bg-orange-900/40"
                  : "border-zinc-300 bg-zinc-50 dark:bg-zinc-800";

              return (
                <div key={`log-${log.id}`} className="flex gap-4 px-5 py-4 border-t border-zinc-100 dark:border-zinc-800">
                  {/* Timeline dot */}
                  <div className="shrink-0 flex flex-col items-center">
                    <div
                      className={`w-5 h-5 rounded-full border-2 flex items-center justify-center z-10 ${dotColor}`}
                    >
                      <span className="text-[8px]">💹</span>
                    </div>
                  </div>
                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                        PricingAgent
                      </span>
                      <span
                        className={`flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded ${PLATFORM_COLOR[platformCode] ?? "bg-zinc-400"} bg-opacity-20`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${PLATFORM_COLOR[platformCode] ?? "bg-zinc-400"}`}
                        />
                        <span className="text-zinc-600 dark:text-zinc-400">{platformName}</span>
                      </span>
                      {decision && (
                        <span
                          className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${decision.cls}`}
                        >
                          {decision.label}
                        </span>
                      )}
                      <span className="text-[10px] text-zinc-400 ml-auto">
                        {formatDate(entry.time)} {formatTime(entry.time)}
                      </span>
                    </div>

                    {/* Trigger chain */}
                    <div className="flex items-center gap-1 mb-1.5">
                      <span className="text-[10px] text-zinc-400">Tetikleyen:</span>
                      <span className="text-[10px] font-medium text-zinc-500">
                        {log.trigger_event === "competitor_price_change" ? "👁 CompetitorWatcher" : "👤"}{" "}
                        {trigger}
                      </span>
                    </div>

                    {/* Reasoning (truncated) */}
                    {log.reasoning && (
                      <p className="text-[11px] text-zinc-500 dark:text-zinc-500 leading-relaxed line-clamp-2">
                        {log.reasoning}
                      </p>
                    )}

                    {/* Price + duration */}
                    <div className="flex items-center gap-3 mt-1.5">
                      {log.old_price != null && log.new_price != null && log.decision === "price_updated" && (
                        <span className="text-[10px] font-mono">
                          <span className="text-zinc-400 line-through">{log.old_price.toFixed(2)} ₺</span>
                          <span className="text-green-600 dark:text-green-400 font-semibold ml-1">
                            → {log.new_price.toFixed(2)} ₺
                          </span>
                        </span>
                      )}
                      {log.tool_calls && log.tool_calls.length > 0 && (
                        <span className="text-[10px] text-zinc-400">
                          {log.tool_calls.length} tool çağrısı
                        </span>
                      )}
                      {log.duration_ms != null && (
                        <span className="text-[10px] text-zinc-400">{log.duration_ms} ms</span>
                      )}
                      {log.confidence_score != null && (
                        <span
                          className={`text-[10px] font-mono ${
                            log.confidence_score >= 80
                              ? "text-green-600"
                              : log.confidence_score >= 60
                              ? "text-yellow-600"
                              : "text-red-600"
                          }`}
                        >
                          güven: {log.confidence_score.toFixed(0)}/100
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
