"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

interface RetryResult {
  errors_retried: number;
  new_platforms_listed: number;
  total_succeeded: number;
  total_failed: number;
}

export function RetryAllButton({ productId }: { productId: number }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const router = useRouter();

  async function handleClick() {
    setLoading(true);
    setResult(null);
    try {
      const httpRes = await fetch(`/api/proxy/api/products/${productId}/retry`, {
        method: "POST",
      });
      if (!httpRes.ok) {
        const text = await httpRes.text().catch(() => "");
        throw new Error(`${httpRes.status}: ${text}`);
      }
      const data: RetryResult = await httpRes.json();
      const parts: string[] = [];
      if (data.total_succeeded > 0) parts.push(`${data.total_succeeded} platformda basarili`);
      if (data.total_failed > 0) parts.push(`${data.total_failed} basarisiz`);
      if (data.total_succeeded === 0 && data.total_failed === 0) {
        setResult("Listelenecek platform yok.");
      } else if (data.total_failed === 0) {
        setResult(`✓ Tumu basarili (${data.total_succeeded})`);
      } else {
        setResult(`${parts.join(", ")}`);
      }
      router.refresh();
    } catch (err) {
      setResult(`Hata: ${err instanceof Error ? err.message : "bilinmiyor"}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={handleClick}
        disabled={loading}
        className="rounded-md border border-zinc-300 dark:border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-50 transition-colors"
      >
        {loading ? "Listeleniyor…" : "Eksikleri Listele"}
      </button>
      {result && (
        <span
          className={`text-xs ${result.startsWith("✓") ? "text-green-600 dark:text-green-400" : result.startsWith("Hata") ? "text-red-500" : "text-zinc-500"}`}
        >
          {result}
        </span>
      )}
    </div>
  );
}
