import Link from "next/link";
import { Logo } from "@/components/logo";

const TIERS = [
  {
    name: "Starter",
    price: "$29",
    period: "/ay",
    tagline: "Yeni başlayan satıcılar için",
    cta: "Ücretsiz Dene",
    ctaHref: "/auth/register",
    highlight: false,
    features: [
      "Maksimum 30 ürün",
      "Günde 3 fiyat taraması",
      "3 platform (Trendyol, Amazon, Mağaza)",
      "Temel fiyat geçmişi",
      "E-posta desteği",
    ],
    missing: [
      "Gerçek zamanlı ajan döngüsü",
      "Akıllı buybox stratejisi",
      "Confidence score & onay akışı",
    ],
  },
  {
    name: "Pro",
    price: "$99",
    period: "/ay",
    tagline: "Büyümekte olan KOBİ'ler için",
    cta: "Pro'ya Geç",
    ctaHref: "/auth/register",
    highlight: true,
    badge: "En Popüler",
    features: [
      "Sınırsız ürün",
      "Gerçek zamanlı ajan loop (5s polling)",
      "Akıllı buybox & kâr-maks stratejileri",
      "Confidence score & insan onay akışı",
      "Canlı SSE log paneli",
      "Dashboard & analytics",
      "Öncelikli destek",
    ],
    missing: [],
  },
  {
    name: "Enterprise",
    price: "Teklif Al",
    period: "",
    tagline: "Büyük markalar & ajanslar için",
    cta: "İletişime Geç",
    ctaHref: "mailto:ahmetakyurt2021@gmail.com?subject=OptiPrice%20Enterprise",
    highlight: false,
    dark: true,
    features: [
      "Her şey Pro'da var +",
      "Sabit aylık ücret",
      "Kurtarılan kârdan %5 başarı payı",
      "Özel strateji geliştirme",
      "Dedicated ajan konfigürasyonu",
      "SLA & 7/24 destek",
      "Özel raporlama & API erişimi",
    ],
    missing: [],
  },
];

const FAQS = [
  {
    q: "Enterprise'daki '%5 başarı payı' nasıl hesaplanır?",
    a: "Ajan, rakip analizi sonucunda fiyatı yukarı çektiğinde (örn. buybox'ta iken %5 artış) elde edilen ekstra kâr üzerinden pay alınır. Fiyat düşüşlerinde veya 'no_action' kararlarında herhangi bir pay alınmaz.",
  },
  {
    q: "Starter'dan Pro'ya geçince ne olur?",
    a: "Ürün limiti kalkar, ajan polling frekansı gerçek zamanlıya geçer ve akıllı strateji motoru (buybox, logistics_balance, profit_max) aktif hale gelir. Tüm geçmiş verileriniz korunur.",
  },
  {
    q: "Gerçek Trendyol / Amazon API'sine bağlanabiliyor musun?",
    a: "Şu an beta aşamasındayız; mock servislerle tam demo akışı mevcut. Gerçek API entegrasyonu (Trendyol Partner, Amazon SP-API) roadmap'te — Enterprise müşterileri için önceliklendirilmiş durumda.",
  },
  {
    q: "İptal politikası nedir?",
    a: "Aylık planlar istediğiniz zaman iptal edilebilir; bir sonraki fatura döneminde erişim sona erer. Enterprise sözleşmeleri özel koşullarla belirlenir.",
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Logo size="md" />
          <div className="hidden md:flex items-center gap-8">
            <Link href="/#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Özellikler
            </Link>
            <Link href="/#how-it-works" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Nasıl Çalışır
            </Link>
            <Link href="/pricing" className="text-sm text-foreground font-medium transition-colors">
              Fiyatlandırma
            </Link>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/auth/login"
              className="text-sm font-medium text-foreground hover:text-muted-foreground transition-colors"
            >
              Giriş Yap
            </Link>
            <Link
              href="/auth/register"
              className="rounded-full bg-primary px-5 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
            >
              Hemen Başla
            </Link>
          </div>
        </div>
      </nav>

      <main className="flex-1 pt-28 pb-20 px-6">
        {/* Hero */}
        <div className="max-w-3xl mx-auto text-center mb-16 animate-slide-up opacity-0 stagger-1">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-xs font-medium text-muted-foreground mb-6 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            Beta — Erken Erişim Fiyatları
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-foreground mb-4">
            Büyüklüğünüze Göre{" "}
            <span className="bg-gradient-to-r from-accent via-blue-500 to-indigo-500 bg-clip-text text-transparent">
              Fiyatlandırma
            </span>
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed">
            Küçük başlayın, büyüdükçe ölçeklendirin. Enterprise&apos;da ajan kazandırdıkça siz kazanırsınız.
          </p>
        </div>

        {/* Tier cards */}
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          {TIERS.map((tier, i) => (
            <div
              key={tier.name}
              className={`relative rounded-2xl border p-8 flex flex-col animate-slide-up opacity-0 ${
                i === 0 ? "stagger-1" : i === 1 ? "stagger-2" : "stagger-3"
              } ${
                tier.dark
                  ? "bg-gradient-to-br from-zinc-900 to-zinc-800 border-zinc-700 text-white"
                  : tier.highlight
                  ? "bg-card border-accent ring-2 ring-accent shadow-xl shadow-accent/10"
                  : "bg-card border-border"
              }`}
            >
              {tier.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="rounded-full bg-accent px-3 py-1 text-xs font-semibold text-white shadow">
                    {tier.badge}
                  </span>
                </div>
              )}

              <div className="mb-6">
                <p className={`text-xs font-semibold uppercase tracking-widest mb-1 ${tier.dark ? "text-zinc-400" : "text-muted-foreground"}`}>
                  {tier.name}
                </p>
                <div className="flex items-baseline gap-1">
                  <span className={`text-4xl font-bold ${tier.dark ? "text-white" : "text-foreground"}`}>
                    {tier.price}
                  </span>
                  {tier.period && (
                    <span className={`text-sm ${tier.dark ? "text-zinc-400" : "text-muted-foreground"}`}>
                      {tier.period}
                    </span>
                  )}
                </div>
                <p className={`text-sm mt-1 ${tier.dark ? "text-zinc-400" : "text-muted-foreground"}`}>
                  {tier.tagline}
                </p>
              </div>

              <ul className="flex-1 space-y-2.5 mb-8">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <span className={`mt-0.5 flex-shrink-0 text-base ${tier.dark ? "text-green-400" : "text-green-500"}`}>✓</span>
                    <span className={tier.dark ? "text-zinc-300" : "text-foreground"}>{f}</span>
                  </li>
                ))}
                {tier.missing.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm opacity-40">
                    <span className="mt-0.5 flex-shrink-0 text-base">✗</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>

              <Link
                href={tier.ctaHref}
                className={`w-full rounded-full py-2.5 text-sm font-semibold text-center transition-all ${
                  tier.dark
                    ? "bg-white text-zinc-900 hover:bg-zinc-100"
                    : tier.highlight
                    ? "bg-primary text-primary-foreground hover:opacity-90"
                    : "bg-secondary text-foreground hover:bg-muted border border-border"
                }`}
              >
                {tier.cta}
              </Link>
            </div>
          ))}
        </div>

        {/* Enterprise profit-share callout */}
        <div className="max-w-3xl mx-auto mb-16 animate-slide-up opacity-0 stagger-3">
          <div className="rounded-2xl border border-border bg-card p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0 text-xl">
                ✦
              </div>
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  Enterprise Başarı Payı — Nasıl Çalışır?
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                  OptiPrice ajanı, buybox&apos;ı elinizde tutarken fiyatınızı yukarı çektiğinde gerçek kâr yaratır.
                  Bu kârın küçük bir payını birlikte paylaşıyoruz — yalnızca ajan başarılı olduğunda.
                </p>
                <div className="rounded-xl bg-secondary border border-border p-4 font-mono text-sm space-y-1">
                  <p className="text-muted-foreground"># Örnek senaryo</p>
                  <p><span className="text-green-500">eski_fiyat</span> = 199.90 ₺</p>
                  <p><span className="text-green-500">yeni_fiyat</span> = 209.90 ₺  <span className="text-muted-foreground"># ajan buybox&apos;ta iken %5 artırdı</span></p>
                  <p><span className="text-green-500">aylık_satış</span> = 100 adet</p>
                  <p className="pt-1"><span className="text-accent">ekstra_kâr</span> = (209.90 - 199.90) × 100 = <span className="font-bold text-foreground">1.000 ₺</span></p>
                  <p><span className="text-accent">başarı_payı</span> = 1.000 × 0.05 = <span className="font-bold text-foreground">50 ₺</span></p>
                  <p><span className="text-green-500">sizin_kazancınız</span> = <span className="font-bold text-foreground">950 ₺ ekstra</span></p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* FAQ */}
        <div className="max-w-2xl mx-auto animate-slide-up opacity-0 stagger-3">
          <h2 className="text-2xl font-bold text-foreground text-center mb-8">Sıkça Sorulan Sorular</h2>
          <div className="space-y-4">
            {FAQS.map((faq, i) => (
              <div key={i} className="rounded-xl border border-border bg-card p-6">
                <h3 className="text-sm font-semibold text-foreground mb-2">{faq.q}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border px-6 py-12">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <Logo size="sm" linkToHome={false} />
          <p className="text-sm text-muted-foreground">
            Hackathon&apos;26 — BTK Akademi x Google x GİRVAK
          </p>
        </div>
      </footer>
    </div>
  );
}
