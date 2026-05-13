import { apiServer, type PricingLog, type Product } from "@/lib/api";
import Link from "next/link";
import { notFound } from "next/navigation";
import { RetryButton } from "./retry-button";
import { RetryAllButton } from "./RetryAllButton";
import { TriggerButton } from "./trigger-button";
import PriceHistoryChart from "./PriceHistoryChart";

async function getProduct(id: string): Promise<Product> {
  try {
    return await apiServer<Product>(`/api/products/${id}`);
  } catch {
    notFound();
  }
}

async function getLogs(platformStatusId: number): Promise<PricingLog[]> {
  try {
    return await apiServer<PricingLog[]>(`/api/pricing/logs/${platformStatusId}?limit=30`);
  } catch {
    return [];
  }
}

const STATUS_LABEL: Record<string, string> = {
  listed: "Listelendi",
  pending: "Beklemede",
  error: "Hata",
};

const STATUS_COLOR: Record<string, string> = {
  listed: "text-green-700 bg-green-50 border-green-200",
  pending: "text-yellow-700 bg-yellow-50 border-yellow-200",
  error: "text-red-700 bg-red-50 border-red-200",
};

const PLATFORM_CODE_COLOR: Record<string, string> = {
  trendyol: "bg-orange-500",
  amazon: "bg-yellow-400",
  own_site: "bg-blue-500",
};

export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const product = await getProduct(id);

  // Fetch price logs for each platform status in parallel
  const logsMap = new Map<number, PricingLog[]>();
  if (product.platform_statuses.length > 0) {
    const results = await Promise.all(
      product.platform_statuses.map((ps) => getLogs(ps.id))
    );
    product.platform_statuses.forEach((ps, i) => {
      logsMap.set(ps.id, results[i]);
    });
  }

  return (
    <div className="p-8">
      <div className="mb-2">
        <Link href="/products" className="text-xs text-zinc-400 hover:text-zinc-600">
          ← Ürünler
        </Link>
      </div>

      <div className="mb-6">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">{product.title}</h1>
        <p className="text-xs text-zinc-400 font-mono mt-1">{product.sku}</p>
      </div>

      {/* Product info */}
      <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-5 mb-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Stat label="Maliyet" value={`${Number(product.base_cost).toFixed(2)} ₺`} />
        <Stat label="Kargo" value={`${Number(product.shipping_cost).toFixed(2)} ₺`} />
        <Stat label="Stok" value={String(product.stock)} />
        <Stat label="Kategori" value={product.category ?? "—"} />
      </div>

      {/* Platform cards */}
      <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">Platform Durumları</h2>
      <div className="mb-4">
        <RetryAllButton productId={product.id} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {product.platform_statuses.map((ps) => (
          <div
            key={ps.platform_code}
            className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden"
          >
            {/* Card header */}
            <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-100 dark:border-zinc-800">
              <span
                className={`w-2.5 h-2.5 rounded-full shrink-0 ${PLATFORM_CODE_COLOR[ps.platform_code] ?? "bg-zinc-400"}`}
              />
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-50 flex-1">
                {ps.platform_name}
              </span>
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded-full border ${STATUS_COLOR[ps.status] ?? "text-zinc-600 bg-zinc-50 border-zinc-200"}`}
              >
                {STATUS_LABEL[ps.status] ?? ps.status}
              </span>
            </div>

            {/* Floor hit warning */}
            {ps.status === "listed" &&
              ps.current_price != null &&
              ps.floor_price != null &&
              !ps.has_buybox &&
              Number(ps.current_price) <= Number(ps.floor_price) * 1.02 && (
                <div className="mx-4 mt-2 rounded-md bg-yellow-50 dark:bg-yellow-950/30 border border-yellow-200 dark:border-yellow-800 px-3 py-2">
                  <p className="text-xs font-medium text-yellow-700 dark:text-yellow-400">
                    ⚠ Marj koruma aktif — Buybox alınamadı
                  </p>
                  <p className="text-[11px] text-yellow-600 dark:text-yellow-500 mt-0.5">
                    Floor fiyatında kaldık, rakip daha düşük.
                  </p>
                </div>
              )}

            {/* Card body */}
            <div className="px-4 py-3 flex flex-col gap-2">
              <Row label="Güncel Fiyat" value={ps.current_price != null ? `${Number(ps.current_price).toFixed(2)} ₺` : "—"} />
              <Row label="Taban Fiyat" value={ps.floor_price != null ? `${Number(ps.floor_price).toFixed(2)} ₺` : "—"} />
              <Row label="Rakip Fiyatı" value={ps.competitor_price != null ? `${Number(ps.competitor_price).toFixed(2)} ₺` : "—"} />
              <Row
                label="Buybox"
                value={ps.has_buybox ? "✓ Bizde" : "✗ Rakipte"}
                highlight={ps.has_buybox ? "green" : undefined}
              />
              <Row label="External ID" value={ps.external_id ?? "—"} mono />
            </div>

            {/* Price history chart */}
            <PriceHistoryChart
              logs={logsMap.get(ps.id) ?? []}
              platformCode={ps.platform_code}
              floorPrice={ps.floor_price}
            />

            {/* Error detail */}
            {ps.status === "error" && ps.error_message && (
              <div className="mx-4 mt-2 rounded-md bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 px-3 py-2">
                <p className="text-xs font-medium text-red-700 dark:text-red-400">Hata Detayı</p>
                <p className="text-[11px] text-red-600 dark:text-red-500 mt-0.5 font-mono break-all">
                  {ps.error_message}
                </p>
              </div>
            )}

            {/* AI title */}
            {ps.ai_generated_title && (
              <div className="px-4 pb-3">
                <p className="text-xs text-zinc-400 mb-1">AI Başlık</p>
                <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed line-clamp-3">
                  {ps.ai_generated_title}
                </p>
              </div>
            )}

            {/* Manual trigger — retry failed listings */}
            {ps.status === "error" && (
              <div className="px-4 pb-4">
                <RetryButton productId={product.id} />
              </div>
            )}
            {ps.status === "listed" && ps.external_id && (
              <div className="px-4 pb-4">
                <TriggerButton productPlatformId={ps.id} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-zinc-400">{label}</p>
      <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50 mt-0.5">{value}</p>
    </div>
  );
}

function Row({
  label,
  value,
  mono,
  highlight,
}: {
  label: string;
  value: string;
  mono?: boolean;
  highlight?: "green";
}) {
  const valueColor =
    highlight === "green"
      ? "text-green-600 dark:text-green-400 font-semibold"
      : "text-zinc-800 dark:text-zinc-200";
  return (
    <div className="flex justify-between items-baseline gap-2">
      <span className="text-xs text-zinc-400 shrink-0">{label}</span>
      <span className={`text-xs text-right ${valueColor} ${mono ? "font-mono" : ""}`}>
        {value}
      </span>
    </div>
  );
}
