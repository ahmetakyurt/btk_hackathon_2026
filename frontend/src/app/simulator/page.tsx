"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { type PlatformSimState, type CompetitorInfo } from "@/lib/api";

const PLATFORM_COLOR: Record<string, string> = {
  trendyol: "bg-orange-500",
  amazon: "bg-yellow-400",
};

function CompetitorRow({
  competitor,
  productPlatformId,
  onUpdated,
}: {
  competitor: CompetitorInfo;
  productPlatformId: number;
  onUpdated: () => void;
}) {
  const [price, setPrice] = useState(Number(competitor.price).toFixed(2));
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const editing = useRef(false);

  useEffect(() => {
    if (!editing.current) {
      setPrice(Number(competitor.price).toFixed(2));
    }
  }, [competitor.price]);

  async function handleUpdate() {
    const parsed = parseFloat(price);
    if (isNaN(parsed) || parsed <= 0) {
      setFeedback("Geçersiz fiyat");
      return;
    }
    setLoading(true);
    setFeedback(null);
    try {
      const r = await fetch("/api/proxy/api/simulator/set-competitor-price", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_platform_id: productPlatformId,
          seller_name: competitor.seller_name,
          price: parsed,
        }),
      });
      if (!r.ok) throw new Error(`${r.status}`);
      setFeedback("✓ Güncellendi");
      onUpdated();
    } catch (err) {
      setFeedback(`Hata: ${err instanceof Error ? err.message : "bilinmiyor"}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-2 py-1.5 border-b border-zinc-100 dark:border-zinc-800 last:border-0">
      <div className="flex-1 min-w-0">
        <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300 truncate block">
          {competitor.seller_name}
        </span>
        {competitor.has_buybox && (
          <span className="text-[10px] text-orange-500 font-semibold">Buybox</span>
        )}
      </div>
      <input
        type="number"
        step="0.01"
        min="0"
        value={price}
        onChange={(e) => setPrice(e.target.value)}
        onFocus={() => { editing.current = true; }}
        onBlur={() => { editing.current = false; }}
        className="w-24 rounded border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 py-1 text-xs text-zinc-900 dark:text-zinc-50 focus:outline-none focus:ring-1 focus:ring-zinc-400"
      />
      <span className="text-xs text-zinc-400">₺</span>
      <button
        onClick={handleUpdate}
        disabled={loading}
        className="rounded bg-zinc-900 dark:bg-zinc-50 px-2.5 py-1 text-xs font-medium text-white dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-200 disabled:opacity-50 transition-colors shrink-0"
      >
        {loading ? "…" : "Güncelle"}
      </button>
      {feedback && (
        <span
          className={`text-[10px] shrink-0 ${feedback.startsWith("✓") ? "text-green-600" : "text-red-500"}`}
        >
          {feedback}
        </span>
      )}
    </div>
  );
}

function PlatformCard({
  state,
  onUpdated,
}: {
  state: PlatformSimState;
  onUpdated: () => void;
}) {
  return (
    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-100 dark:border-zinc-800">
        <span
          className={`w-2.5 h-2.5 rounded-full shrink-0 ${PLATFORM_COLOR[state.platform_code] ?? "bg-zinc-400"}`}
        />
        <div className="flex-1 min-w-0">
          <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
            {state.platform_name}
          </span>
          <span className="ml-2 text-xs text-zinc-400 font-mono">{state.sku}</span>
        </div>
        <div className="text-right">
          <p className="text-xs text-zinc-400">Bizim</p>
          <p className="text-sm font-bold text-zinc-900 dark:text-zinc-50">
            {Number(state.own_price).toFixed(2)} ₺
          </p>
          {state.own_has_buybox && (
            <p className="text-[10px] text-green-600 font-semibold">Buybox ✓</p>
          )}
        </div>
      </div>

      {/* Competitors */}
      <div className="px-4 py-2">
        <p className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1.5">Rakipler</p>
        {state.competitors.length === 0 ? (
          <div className="rounded-md bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 px-3 py-2">
            <p className="text-[11px] text-amber-700 dark:text-amber-400">
              Mock serviste rakip verisi yok.
            </p>
            <p className="text-[10px] text-amber-600 dark:text-amber-500 mt-0.5">
              Ürün sayfasından &quot;Yeniden Listele&quot; yaparak rakipleri oluşturabilirsiniz.
            </p>
          </div>
        ) : (
          state.competitors.map((c) => (
            <CompetitorRow
              key={c.seller_name}
              competitor={c}
              productPlatformId={state.product_platform_id}
              onUpdated={onUpdated}
            />
          ))
        )}
      </div>

      {/* Product title */}
      <div className="px-4 pb-3">
        <p className="text-[10px] text-zinc-400 truncate">{state.product_title}</p>
      </div>
    </div>
  );
}

export default function SimulatorPage() {
  const [states, setStates] = useState<PlatformSimState[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadState = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const r = await fetch("/api/proxy/api/simulator/state", { cache: "no-store" });
      if (!r.ok) throw new Error(`${r.status}`);
      const data = (await r.json()) as PlatformSimState[];
      setStates(data);
      setError(null);
    } catch (err) {
      setError(`Yüklenemedi: ${err instanceof Error ? err.message : "bilinmiyor"}`);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadState();
  }, [loadState]);

  const grouped = states.reduce<Record<string, PlatformSimState[]>>((acc, s) => {
    const key = s.sku;
    if (!acc[key]) acc[key] = [];
    acc[key].push(s);
    return acc;
  }, {});

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Rakip Simülatörü</h1>
        <p className="text-sm text-zinc-400 mt-1">
          Rakip fiyatını değiştir → Ajan otomatik tepki verir → Canlı Loglar&apos;da izle
        </p>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-24">
          <p className="text-zinc-400 text-sm">Yükleniyor…</p>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-900 p-4 text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {!loading && !error && Object.keys(grouped).length === 0 && (
        <div className="rounded-xl border border-dashed border-zinc-300 dark:border-zinc-700 p-16 text-center">
          <p className="text-zinc-500 text-sm">
            Henüz listelenmiş ürün yok. Önce bir ürün ekle ve platformlara gönder.
          </p>
        </div>
      )}

      <div className="flex flex-col gap-8">
        {Object.entries(grouped).map(([sku, platformStates]) => (
          <div key={sku}>
            <h2 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 mb-3 font-mono">
              {sku} — {platformStates[0]?.product_title}
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {platformStates.map((s) => (
                <PlatformCard key={s.product_platform_id} state={s} onUpdated={() => loadState(true)} />
              ))}
            </div>
          </div>
        ))}
      </div>

      {states.length > 0 && (
        <div className="mt-6">
          <button
            onClick={() => loadState(true)}
            disabled={refreshing}
            className="text-xs text-zinc-400 hover:text-zinc-600 disabled:opacity-50 transition-colors"
          >
            {refreshing ? "Yükleniyor…" : "↻ Yenile"}
          </button>
        </div>
      )}
    </div>
  );
}
