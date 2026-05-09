"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function TriggerButton({ productPlatformId }: { productPlatformId: number }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function handleClick() {
    setLoading(true);
    setResult(null);
    try {
      const res = await api<{ decision: string; old_price: number | null; new_price: number | null }>(
        `/api/pricing/trigger/${productPlatformId}`,
        { method: "POST" }
      );
      const label =
        res.decision === "price_updated"
          ? `✓ ${res.old_price?.toFixed(2)} → ${res.new_price?.toFixed(2)} ₺`
          : res.decision === "floor_hit"
          ? "⚠ Floor'da kaldı"
          : "— Değişiklik yok";
      setResult(label);
    } catch (err) {
      setResult(`Hata: ${err instanceof Error ? err.message : "bilinmiyor"}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <button
        onClick={handleClick}
        disabled={loading}
        className="w-full rounded-md border border-zinc-200 dark:border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 disabled:opacity-50 transition-colors"
      >
        {loading ? "Ajan çalışıyor…" : "Manuel Fiyatlandır"}
      </button>
      {result && (
        <p className="text-xs text-center text-zinc-500">{result}</p>
      )}
    </div>
  );
}
