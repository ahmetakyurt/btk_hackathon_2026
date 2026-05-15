import { auth } from "@/auth";
import { redirect } from "next/navigation";
import Link from "next/link";

// Demo: mevcut plan Pro olarak sabitlendi
const CURRENT_PLAN = "pro";

const TIERS = [
  {
    id: "starter",
    name: "Starter",
    price: "$29",
    period: "/ay",
    tagline: "Yeni başlayan satıcılar için",
    features: [
      "Maksimum 30 ürün",
      "Günde 3 fiyat taraması",
      "3 platform desteği",
      "Temel fiyat geçmişi",
    ],
  },
  {
    id: "pro",
    name: "Pro",
    price: "$99",
    period: "/ay",
    tagline: "Büyümekte olan KOBİ'ler için",
    features: [
      "Her şey Starter'da var +",
      "Sınırsız ürün",
      "Gerçek zamanlı ajan loop (5s polling)",
      "Akıllı buybox & kâr-maks stratejileri",
      "Confidence score & insan onay akışı",
      "Canlı SSE log paneli",
      "Dashboard & analytics",
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "Sabit ücret",
    period: "+ %5 başarı payı",
    tagline: "Büyük markalar & ajanslar için",
    features: [
      "Her şey Pro'da var +",
      "Özel strateji geliştirme",
      "Dedicated ajan konfigürasyonu",
      "SLA & 7/24 destek",
      "Özel raporlama & API erişimi",
    ],
  },
];

const FAQS = [
  {
    q: "Enterprise'daki '%5 başarı payı' nasıl hesaplanır?",
    a: "Ajan, rakip analizi sonucunda fiyatı yukarı çektiğinde elde edilen ekstra kâr üzerinden pay alınır. Fiyat düşüşlerinde veya 'no_action' kararlarında herhangi bir pay alınmaz.",
  },
  {
    q: "Pro'dan Enterprise'a geçince ne değişir?",
    a: "Tüm Pro özellikleri korunur. Ek olarak özel strateji konfigürasyonu, SLA garantisi ve başarı bazlı fiyatlandırma modeli aktif hale gelir.",
  },
  {
    q: "Gerçek Trendyol / Amazon API'sine bağlanabiliyor musun?",
    a: "Şu an beta aşamasındayız; mock servislerle tam demo akışı mevcut. Gerçek API entegrasyonu Enterprise müşterileri için önceliklendirilmiş durumda.",
  },
  {
    q: "İptal politikası nedir?",
    a: "Aylık planlar istediğiniz zaman iptal edilebilir; bir sonraki fatura döneminde erişim sona erer. Enterprise sözleşmeleri özel koşullarla belirlenir.",
  },
];

const TIER_ORDER = ["starter", "pro", "enterprise"];

function tierCmp(tierId: string): "current" | "downgrade" | "upgrade" {
  const cur = TIER_ORDER.indexOf(CURRENT_PLAN);
  const t = TIER_ORDER.indexOf(tierId);
  if (t === cur) return "current";
  return t < cur ? "downgrade" : "upgrade";
}

export default async function PlanPage() {
  const session = await auth();
  if (!session?.user?.id) redirect("/auth/login");

  const currentTier = TIERS.find((t) => t.id === CURRENT_PLAN)!;

  return (
    <div className="p-8">
      <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 mb-2">Planım & Abonelik</h1>
      <p className="text-sm text-zinc-500 mb-8">Mevcut planınızı görüntüleyin veya daha üst bir plana geçin.</p>

      {/* Current plan summary */}
      <div className="rounded-xl border border-green-200 dark:border-green-900 bg-green-50 dark:bg-green-950/20 p-5 mb-8 flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-green-600 dark:text-green-400 mb-1">
            Güncel Planınız
          </p>
          <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
            {currentTier.name}{" "}
            <span className="text-base font-normal text-zinc-500">{currentTier.price}{currentTier.period}</span>
          </p>
          <p className="text-sm text-zinc-500 mt-0.5">{currentTier.tagline}</p>
        </div>
        <span className="flex-shrink-0 rounded-full bg-green-100 dark:bg-green-900/40 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 text-xs font-semibold px-3 py-1.5">
          Aktif
        </span>
      </div>

      {/* Plan comparison */}
      <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-4">Plan Karşılaştırması</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-10">
        {TIERS.map((tier) => {
          const rel = tierCmp(tier.id);
          const isCurrent = rel === "current";
          const isEnterprise = tier.id === "enterprise";

          return (
            <div
              key={tier.id}
              className={`relative rounded-xl border p-6 flex flex-col ${
                isEnterprise
                  ? "bg-gradient-to-br from-zinc-900 to-zinc-800 border-zinc-700 text-white"
                  : isCurrent
                  ? "bg-white dark:bg-zinc-900 border-accent ring-2 ring-accent shadow-lg shadow-accent/10"
                  : "bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800"
              }`}
            >
              {isCurrent && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="rounded-full bg-green-500 px-3 py-1 text-xs font-semibold text-white shadow">
                    Mevcut Plan
                  </span>
                </div>
              )}

              <div className="mb-5">
                <p className={`text-xs font-semibold uppercase tracking-widest mb-1 ${isEnterprise ? "text-zinc-400" : "text-zinc-500"}`}>
                  {tier.name}
                </p>
                <div className="flex items-baseline gap-1">
                  <span className={`text-3xl font-bold ${isEnterprise ? "text-white" : "text-zinc-900 dark:text-zinc-50"}`}>
                    {tier.price}
                  </span>
                  {tier.period && (
                    <span className={`text-sm ${isEnterprise ? "text-zinc-400" : "text-zinc-500"}`}>
                      {tier.period}
                    </span>
                  )}
                </div>
                <p className={`text-xs mt-1 ${isEnterprise ? "text-zinc-400" : "text-zinc-500"}`}>
                  {tier.tagline}
                </p>
              </div>

              <ul className="flex-1 space-y-2 mb-6">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <span className={`mt-0.5 flex-shrink-0 ${isEnterprise ? "text-green-400" : "text-green-500"}`}>✓</span>
                    <span className={isEnterprise ? "text-zinc-300" : "text-zinc-700 dark:text-zinc-300"}>{f}</span>
                  </li>
                ))}
              </ul>

              {isCurrent ? (
                <button
                  disabled
                  className="w-full rounded-lg py-2 text-sm font-semibold bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 border border-green-200 dark:border-green-800 cursor-default"
                >
                  Mevcut Plan
                </button>
              ) : rel === "downgrade" ? (
                <button
                  disabled
                  className="w-full rounded-lg py-2 text-sm font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-400 border border-zinc-200 dark:border-zinc-700 cursor-not-allowed"
                  title="Mevcut plandan düşük"
                >
                  Düşür
                </button>
              ) : isEnterprise ? (
                <Link
                  href="mailto:ahmetakyurt2021@gmail.com?subject=OptiPrice%20Enterprise%20Teklif"
                  className="w-full rounded-lg py-2 text-sm font-semibold text-center bg-white text-zinc-900 hover:bg-zinc-100 transition-colors"
                >
                  İletişime Geç
                </Link>
              ) : (
                <Link
                  href="/auth/register"
                  className="w-full rounded-lg py-2 text-sm font-semibold text-center bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 hover:opacity-90 transition-opacity"
                >
                  Yükselt
                </Link>
              )}
            </div>
          );
        })}
      </div>

      {/* Enterprise profit-share callout */}
      <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-6 mb-8">
        <div className="flex items-start gap-4">
          <div className="w-9 h-9 rounded-lg bg-accent/10 flex items-center justify-center flex-shrink-0 text-lg">
            ✦
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50 mb-2">
              Enterprise Başarı Payı — Nasıl Çalışır?
            </h3>
            <p className="text-sm text-zinc-500 leading-relaxed mb-4">
              Ajan buybox&apos;ı elinizde tutarken fiyatınızı yukarı çektiğinde gerçek kâr yaratır.
              Bu kârın küçük bir payını birlikte paylaşıyoruz — yalnızca ajan başarılı olduğunda.
            </p>
            <div className="rounded-lg bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 p-4 font-mono text-xs space-y-1">
              <p className="text-zinc-400"># Örnek senaryo</p>
              <p><span className="text-green-500">eski_fiyat</span> = 199.90 ₺</p>
              <p><span className="text-green-500">yeni_fiyat</span> = 209.90 ₺ <span className="text-zinc-400"># ajan %5 artırdı</span></p>
              <p><span className="text-green-500">aylık_satış</span> = 100 adet</p>
              <p className="pt-1"><span className="text-accent">ekstra_kâr</span> = <span className="font-bold text-zinc-900 dark:text-zinc-50">1.000 ₺</span></p>
              <p><span className="text-accent">başarı_payı</span> = 1.000 × 0.05 = <span className="font-bold text-zinc-900 dark:text-zinc-50">50 ₺</span></p>
              <p><span className="text-green-500">sizin_kazancınız</span> = <span className="font-bold text-zinc-900 dark:text-zinc-50">950 ₺ ekstra</span></p>
            </div>
          </div>
        </div>
      </div>

      {/* FAQ */}
      <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-4">Sıkça Sorulan Sorular</h2>
      <div className="space-y-3">
        {FAQS.map((faq, i) => (
          <div key={i} className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-5">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50 mb-1.5">{faq.q}</h3>
            <p className="text-sm text-zinc-500 leading-relaxed">{faq.a}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
