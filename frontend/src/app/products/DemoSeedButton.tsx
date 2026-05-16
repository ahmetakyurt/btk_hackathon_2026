"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function DemoSeedButton() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function handleSeed() {
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await fetch("/api/proxy/api/demo/seed", { method: "POST" });
      if (!res.ok) {
        const text = await res.json().then((j) => j.detail).catch(() => "Bilinmeyen hata");
        throw new Error(text);
      }
      const data = await res.json();
      setResult(
        `${data.products_created} ürün eklendi, ${data.products_skipped} mevcut atlandı.`
      );
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Bilinmeyen hata");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        onClick={handleSeed}
        disabled={loading}
        className="rounded-md border border-zinc-300 dark:border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-50 transition-colors"
      >
        {loading ? "Yükleniyor..." : "Demo verisini yükle"}
      </button>
      {result && (
        <p className="text-xs text-green-600 dark:text-green-400">{result}</p>
      )}
      {error && (
        <p className="text-xs text-red-500">{error}</p>
      )}
    </div>
  );
}
