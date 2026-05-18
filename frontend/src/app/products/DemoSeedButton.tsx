"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function DemoSeedButton({ reset = false, label }: { reset?: boolean; label?: string } = {}) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function handleSeed() {
    if (reset && !confirm("Mevcut ürünler, fiyatlandırma logları ve platform bağlantıların silinip demo verisi yeniden yüklenecek. Devam edilsin mi?")) {
      return;
    }
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const url = reset ? "/api/proxy/api/demo/seed?reset=true" : "/api/proxy/api/demo/seed";
      const res = await fetch(url, { method: "POST" });
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
        className={
          reset
            ? "rounded-md border border-red-300 dark:border-red-800 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/20 disabled:opacity-50 transition-colors"
            : "rounded-md border border-zinc-300 dark:border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-50 transition-colors"
        }
      >
        {loading ? "Yükleniyor..." : (label ?? "Demo verisini yükle")}
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

export function ResetPricesButton() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function handleReset() {
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await fetch("/api/proxy/api/demo/reset-prices", { method: "POST" });
      if (!res.ok) {
        const text = await res.json().then((j) => j.detail).catch(() => "Bilinmeyen hata");
        throw new Error(text);
      }
      const data = await res.json();
      const failNote = data.push_failures > 0 ? ` (${data.push_failures} platform push başarısız)` : "";
      setResult(`${data.reset_count} ürün fiyatı sıfırlandı.${failNote}`);
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
        onClick={handleReset}
        disabled={loading}
        className="rounded-md border border-amber-300 dark:border-amber-700 px-4 py-2 text-sm font-medium text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 disabled:opacity-50 transition-colors"
      >
        {loading ? "Sıfırlanıyor..." : "Fiyatları Sıfırla"}
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
