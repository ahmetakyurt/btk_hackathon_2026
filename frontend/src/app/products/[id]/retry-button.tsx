"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function RetryButton({ productId }: { productId: number }) {
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
      setResult("✓ Listelendi");
      router.refresh();
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
        className="w-full rounded-md border border-red-200 dark:border-red-800 px-3 py-1.5 text-xs font-medium text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 disabled:opacity-50 transition-colors"
      >
        {loading ? "Listeleniyor…" : "Yeniden Listele"}
      </button>
      {result && (
        <p className="text-xs text-center text-zinc-500">{result}</p>
      )}
    </div>
  );
}
