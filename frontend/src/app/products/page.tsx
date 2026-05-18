import { apiServer, type Product } from "@/lib/api";
import Link from "next/link";
import { DemoSeedButton, ResetPricesButton } from "./DemoSeedButton";

async function getProducts(): Promise<{ data: Product[]; error: string | null }> {
  try {
    const data = await apiServer<Product[]>("/api/products");
    return { data, error: null };
  } catch (err) {
    return { data: [], error: err instanceof Error ? err.message : "Bilinmeyen hata" };
  }
}

const STATUS_BADGE: Record<string, string> = {
  listed: "bg-green-100 text-green-700",
  pending: "bg-yellow-100 text-yellow-700",
  error: "bg-red-100 text-red-700",
};

export default async function ProductsPage() {
  const { data: products, error } = await getProducts();

  return (
    <div className="p-8">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Ürünler</h1>
        <div className="flex items-center gap-2 flex-wrap">
          {products.length > 0 && <DemoSeedButton reset label="Demo'yu Yenile" />}
          <ResetPricesButton />
          <Link
            href="/products/new"
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200 transition-colors"
          >
            + Yeni Ürün
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-900 p-4 text-sm text-red-600 dark:text-red-400 mb-4">
          Backend&apos;e bağlanılamadı: {error}
        </div>
      )}

      {!error && products.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-300 dark:border-zinc-700 p-16 text-center">
          <p className="text-zinc-500 text-sm mb-4">Henüz ürün yok. Yeni ürün ekle ya da demo verisiyle başla.</p>
          <div className="flex items-center justify-center gap-3">
            <Link
              href="/products/new"
              className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-200 transition-colors"
            >
              + Yeni Ürün
            </Link>
            <DemoSeedButton />
          </div>
        </div>
      ) : products.length > 0 ? (
        <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 overflow-hidden bg-white dark:bg-zinc-900">
          <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[640px]">
            <thead className="bg-zinc-50 dark:bg-zinc-800 text-left">
              <tr>
                <th className="px-4 py-3 font-medium text-zinc-500">SKU</th>
                <th className="px-4 py-3 font-medium text-zinc-500">Ürün Adı</th>
                <th className="px-4 py-3 font-medium text-zinc-500">Kategori</th>
                <th className="px-4 py-3 font-medium text-zinc-500">Maliyet</th>
                <th className="px-4 py-3 font-medium text-zinc-500">Stok</th>
                <th className="px-4 py-3 font-medium text-zinc-500">Platformlar</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {products.map((product) => (
                <tr
                  key={product.id}
                  className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-xs text-zinc-500">{product.sku}</td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/products/${product.id}`}
                      className="font-medium text-zinc-900 dark:text-zinc-50 hover:underline"
                    >
                      {product.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-zinc-500">{product.category ?? "—"}</td>
                  <td className="px-4 py-3 text-zinc-900 dark:text-zinc-50">
                    {Number(product.base_cost).toFixed(2)} ₺
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-zinc-900 dark:text-zinc-50">{product.stock}</span>
                    {product.stock > 0 && product.stock <= 10 && (
                      <span className="ml-1.5 rounded-full px-1.5 py-0.5 text-[10px] font-medium bg-red-100 text-red-700">
                        Düşük Stok
                      </span>
                    )}
                    {product.stock === 0 && (
                      <span className="ml-1.5 rounded-full px-1.5 py-0.5 text-[10px] font-medium bg-zinc-200 text-zinc-600">
                        Tükendi
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1.5 flex-wrap">
                      {product.platform_statuses.map((ps) => (
                        <span
                          key={ps.platform_code}
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[ps.status] ?? "bg-zinc-100 text-zinc-600"}`}
                        >
                          {ps.platform_name}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}
