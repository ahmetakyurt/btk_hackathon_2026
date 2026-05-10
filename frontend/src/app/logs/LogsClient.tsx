"use client";

import { useEffect, useRef, useState } from "react";
import { type PricingLog, type ToolCallEntry } from "@/lib/api";

const DECISION_COLOR: Record<string, string> = {
  price_updated: "text-green-400",
  floor_hit: "text-yellow-400",
  no_action: "text-zinc-400",
};

const PLATFORM_LABEL: Record<string, string> = {
  trendyol: "Trendyol",
  amazon: "Amazon",
  own_site: "Kendi Site",
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("tr-TR", { hour12: false });
  } catch {
    return iso;
  }
}

function ToolCallRow({ tc }: { tc: ToolCallEntry }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="ml-4">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <span className="text-zinc-600">{open ? "▾" : "▸"}</span>
        <span className="text-cyan-500">tool:</span>{" "}
        <span className="text-cyan-300">{tc.tool}</span>
        {tc.result && "success" in tc.result && (
          <span className={tc.result.success ? "text-green-500" : "text-red-500"}>
            {tc.result.success ? " ✓" : " ✗"}
          </span>
        )}
      </button>
      {open && (
        <div className="mt-1 ml-4 text-xs">
          {Object.keys(tc.args).length > 0 && (
            <div>
              <span className="text-zinc-500">args: </span>
              <span className="text-zinc-300">{JSON.stringify(tc.args)}</span>
            </div>
          )}
          <div>
            <span className="text-zinc-500">result: </span>
            <span className="text-zinc-300">{JSON.stringify(tc.result)}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function LogEntry({ log }: { log: PricingLog }) {
  const decisionColor = DECISION_COLOR[log.decision] ?? "text-zinc-400";
  const platformLabel = log.platform_code ? (PLATFORM_LABEL[log.platform_code] ?? log.platform_code) : "—";

  return (
    <div className="border-b border-zinc-800 py-3 font-mono text-xs leading-relaxed">
      <div className="flex items-baseline gap-2 flex-wrap">
        <span className="text-zinc-500 shrink-0">[{formatTime(log.created_at)}]</span>
        <span className="text-purple-400 font-semibold">{log.agent_name}</span>
        <span className="text-zinc-500">·</span>
        <span className="text-blue-400">{platformLabel}</span>
        {log.sku && (
          <>
            <span className="text-zinc-500">/</span>
            <span className="text-zinc-300">{log.sku}</span>
          </>
        )}
        <span className="text-zinc-500">·</span>
        <span className="text-zinc-500 italic">{log.trigger_event}</span>
      </div>

      {log.tool_calls && log.tool_calls.length > 0 && (
        <div className="mt-1.5 flex flex-col gap-0.5">
          {log.tool_calls.map((tc, i) => (
            <ToolCallRow key={i} tc={tc} />
          ))}
        </div>
      )}

      {log.reasoning && (
        <div className="mt-1.5 ml-4 text-zinc-400">
          <span className="text-zinc-600">↳ reasoning: </span>
          {log.reasoning}
        </div>
      )}

      <div className="mt-1.5 ml-4">
        <span className="text-zinc-600">↳ DECISION: </span>
        <span className={`font-semibold ${decisionColor}`}>{log.decision}</span>
        {log.old_price != null && log.new_price != null && log.decision === "price_updated" && (
          <span className="text-zinc-400">
            {" "}({Number(log.old_price).toFixed(2)} → {Number(log.new_price).toFixed(2)} ₺)
          </span>
        )}
        {log.decision === "floor_hit" && log.new_price != null && (
          <span className="text-zinc-400"> (floor={Number(log.new_price).toFixed(2)} ₺)</span>
        )}
        {log.duration_ms != null && (
          <span className="text-zinc-600"> in {log.duration_ms}ms</span>
        )}
      </div>
    </div>
  );
}

export default function LogsClient({ userId }: { userId: string }) {
  const [logs, setLogs] = useState<PricingLog[]>([]);
  const [connected, setConnected] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  // Initial load via authenticated proxy
  useEffect(() => {
    fetch(`/api/proxy/api/pricing/logs?limit=50`)
      .then((r) => r.json())
      .then((data: PricingLog[]) => setLogs(data.reverse()))
      .catch(() => {});
  }, []);

  // SSE stream — user_id passed as query param (EventSource can't set headers)
  useEffect(() => {
    const API_BASE =
      process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    const sseUrl = `${API_BASE}/api/agents/logs/stream?user_id=${userId}`;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      const es = new EventSource(sseUrl);
      esRef.current = es;

      es.onopen = () => setConnected(true);

      es.onerror = () => {
        setConnected(false);
        es.close();
        retryTimer = setTimeout(connect, 3000);
      };

      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data as string) as { type?: string } & PricingLog;
          if (data.type === "connected") return;
          setLogs((prev) => {
            const next = [...prev, data as PricingLog];
            return next.length > 100 ? next.slice(-100) : next;
          });
        } catch {}
      };
    }

    connect();

    return () => {
      esRef.current?.close();
      if (retryTimer) clearTimeout(retryTimer);
      setConnected(false);
    };
  }, [userId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 shrink-0">
        <div>
          <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">Canlı Loglar</h1>
          <p className="text-xs text-zinc-400 mt-0.5">Ajan kararları gerçek zamanlı akıyor</p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${connected ? "bg-green-500 animate-pulse" : "bg-zinc-400"}`}
          />
          <span className="text-xs text-zinc-500">{connected ? "Bağlı" : "Bağlantı bekleniyor…"}</span>
        </div>
      </div>

      {/* Terminal */}
      <div className="flex-1 overflow-auto bg-zinc-950 p-4">
        {logs.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-zinc-600 font-mono text-sm">
              Henüz log yok. Ajan kararları burada görünecek…
            </p>
          </div>
        ) : (
          <div>
            {logs.map((log, i) => (
              <LogEntry key={log.id ?? i} log={log} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
