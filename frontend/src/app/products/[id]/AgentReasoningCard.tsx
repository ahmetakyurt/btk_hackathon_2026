"use client";

import { useState } from "react";
import type { PricingLog } from "@/lib/api";

const DECISION_COLOR: Record<string, string> = {
  price_updated: "text-green-700 bg-green-50 border-green-200",
  floor_hit: "text-yellow-700 bg-yellow-50 border-yellow-200",
  no_action: "text-zinc-600 bg-zinc-50 border-zinc-200",
  pending_approval: "text-orange-700 bg-orange-50 border-orange-200",
};

const DECISION_LABEL: Record<string, string> = {
  price_updated: "Fiyat Güncellendi",
  floor_hit: "Floor Hit",
  no_action: "İşlem Yok",
  pending_approval: "Onay Bekliyor",
};

function ConfidenceBar({ score }: { score: number }) {
  const color =
    score >= 80 ? "bg-green-500" : score >= 60 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
      <span className="text-[10px] text-zinc-500 w-7 text-right shrink-0">
        {score.toFixed(0)}
      </span>
    </div>
  );
}

export function AgentReasoningCard({ log }: { log: PricingLog }) {
  const [expanded, setExpanded] = useState(false);

  const decisionColor = DECISION_COLOR[log.decision] ?? DECISION_COLOR.no_action;
  const decisionLabel = DECISION_LABEL[log.decision] ?? log.decision;

  return (
    <div className="mx-4 mb-3 rounded-lg border border-zinc-200 dark:border-zinc-700 overflow-hidden text-left">
      {/* Header — always visible */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 bg-zinc-50 dark:bg-zinc-800/60 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[11px]">🤖</span>
          <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300 shrink-0">
            Son Ajan Kararı
          </span>
          <span
            className={`text-[10px] font-medium px-1.5 py-0.5 rounded border shrink-0 ${decisionColor}`}
          >
            {decisionLabel}
          </span>
        </div>
        <span className="text-[10px] text-zinc-400 shrink-0 ml-2">
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {/* Confidence bar — always visible if score exists */}
      {log.confidence_score != null && (
        <div className="px-3 py-2 bg-zinc-50 dark:bg-zinc-800/30 border-t border-zinc-100 dark:border-zinc-700">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-zinc-400">Güven Skoru</span>
            <span className="text-[10px] text-zinc-400">
              {log.confidence_score.toFixed(0)}/100
            </span>
          </div>
          <ConfidenceBar score={log.confidence_score} />
        </div>
      )}

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-zinc-100 dark:border-zinc-700">
          {/* Reasoning */}
          {log.reasoning && (
            <div className="px-3 py-2.5">
              <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide mb-1">
                Ajan Gerekçesi
              </p>
              <p className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed">
                {log.reasoning}
              </p>
            </div>
          )}

          {/* Tool calls */}
          {log.tool_calls && log.tool_calls.length > 0 && (
            <div className="px-3 py-2 border-t border-zinc-100 dark:border-zinc-700">
              <p className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wide mb-1.5">
                Araç Çağrıları ({log.tool_calls.length})
              </p>
              <div className="flex flex-col gap-1">
                {log.tool_calls.map((tc, i) => (
                  <div
                    key={i}
                    className="rounded bg-zinc-100 dark:bg-zinc-800 px-2 py-1.5 flex items-start gap-2"
                  >
                    <span className="text-[10px] font-mono font-bold text-blue-600 dark:text-blue-400 shrink-0">
                      {tc.tool}
                    </span>
                    {tc.result && typeof tc.result === "object" && (
                      <span className="text-[10px] text-zinc-500 font-mono truncate">
                        →{" "}
                        {JSON.stringify(tc.result)
                          .replace(/[{}"]/g, "")
                          .slice(0, 60)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Price change */}
          {(log.old_price != null || log.new_price != null) && (
            <div className="px-3 py-2 border-t border-zinc-100 dark:border-zinc-700 flex items-center gap-3">
              <span className="text-[10px] text-zinc-400">Fiyat</span>
              {log.old_price != null && (
                <span className="text-[10px] font-mono text-zinc-500 line-through">
                  {log.old_price.toFixed(2)} ₺
                </span>
              )}
              {log.new_price != null && (
                <span className="text-[10px] font-mono font-semibold text-green-600 dark:text-green-400">
                  → {log.new_price.toFixed(2)} ₺
                </span>
              )}
            </div>
          )}

          {/* Meta */}
          <div className="px-3 py-1.5 border-t border-zinc-100 dark:border-zinc-700 flex items-center justify-between">
            <span className="text-[10px] text-zinc-400 font-mono">{log.trigger_event}</span>
            {log.duration_ms != null && (
              <span className="text-[10px] text-zinc-400">{log.duration_ms} ms</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
