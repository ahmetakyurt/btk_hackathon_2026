import { auth } from "@/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { Logo } from "@/components/logo";
import { MobileNav } from "@/components/mobile-nav";

export default async function HomePage() {
  const session = await auth();
  if (session?.user) redirect("/dashboard");

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground overflow-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Logo size="md" />
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Özellikler
            </a>
            <a href="#how-it-works" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Nasıl Çalışır
            </a>
            <a href="#platforms" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Platformlar
            </a>
            <Link href="/pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Fiyatlandırma
            </Link>
          </div>
          <div className="hidden md:flex items-center gap-3">
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
          <MobileNav />
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6 flex-1 flex flex-col items-center justify-center min-h-screen">
        {/* Floating decorative elements */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-10 w-72 h-72 bg-accent/5 rounded-full blur-3xl animate-pulse-glow" />
          <div className="absolute bottom-1/4 right-10 w-96 h-96 bg-muted/50 rounded-full blur-3xl animate-pulse-glow" style={{ animationDelay: "1.5s" }} />
        </div>

        {/* Announcement badge */}
        <div className="animate-slide-up opacity-0 stagger-1">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-xs font-medium text-muted-foreground mb-8 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            Hackathon&apos;26 — BTK x Google x GİRVAK
          </div>
        </div>

        {/* Main headline */}
        <div className="max-w-4xl mx-auto text-center animate-slide-up opacity-0 stagger-2">
          <h1 className="text-4xl sm:text-5xl lg:text-7xl font-bold tracking-tight text-balance leading-tight">
            Çok Kanallı{" "}
            <span className="relative">
              <span className="bg-gradient-to-r from-accent via-blue-500 to-indigo-500 bg-clip-text text-transparent">
                Otonom Fiyatlandırma
              </span>
              <svg className="absolute -bottom-2 left-0 w-full h-3 text-accent/30" viewBox="0 0 200 8" fill="none">
                <path d="M1 5.5C47 2.5 153 2.5 199 5.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </span>{" "}
            Ajanı
          </h1>

          <p className="mt-8 text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto text-balance leading-relaxed">
            Ürünlerinizi bir kez tanımlayın. Yapay zeka ajanlarımız her platformda sizin için listelesin, fiyatlasın ve rakipleri izlesin.
          </p>
        </div>

        {/* CTA buttons */}
        <div className="mt-12 flex flex-col sm:flex-row items-center gap-4 animate-slide-up opacity-0 stagger-3">
          <Link
            href="/auth/register"
            className="group rounded-full bg-primary px-8 py-3.5 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-all flex items-center gap-2 shadow-lg shadow-primary/20"
          >
            Ücretsiz Deneyin
            <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </Link>
          <Link
            href="#how-it-works"
            className="rounded-full border border-border px-8 py-3.5 text-sm font-medium text-foreground hover:bg-secondary transition-colors"
          >
            Nasıl Çalışır?
          </Link>
        </div>

        {/* Floating cards preview */}
        <div className="relative mt-20 w-full max-w-5xl mx-auto animate-fade-in opacity-0 stagger-4">
          <div className="relative">
            {/* Main dashboard preview card */}
            <div className="relative z-10 rounded-2xl border border-border bg-card shadow-2xl shadow-primary/5 overflow-hidden">
              <div className="bg-secondary/50 px-4 py-3 border-b border-border flex items-center gap-2">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-400" />
                  <div className="w-3 h-3 rounded-full bg-yellow-400" />
                  <div className="w-3 h-3 rounded-full bg-green-400" />
                </div>
                <div className="flex-1 text-center">
                  <span className="text-xs text-muted-foreground">OptiPrice AI Dashboard</span>
                </div>
              </div>
              <div className="p-6 bg-gradient-to-br from-card to-secondary/30">
                <div className="grid grid-cols-3 gap-4">
                  <div className="rounded-xl bg-card border border-border p-4 animate-float">
                    <div className="text-xs text-muted-foreground mb-1">Toplam Ürün</div>
                    <div className="text-2xl font-bold">1,247</div>
                    <div className="text-xs text-green-500 mt-1">+12% bu hafta</div>
                  </div>
                  <div className="rounded-xl bg-card border border-border p-4 animate-float-delayed">
                    <div className="text-xs text-muted-foreground mb-1">Aktif Platform</div>
                    <div className="text-2xl font-bold">3</div>
                    <div className="text-xs text-muted-foreground mt-1">Trendyol, Amazon, Web</div>
                  </div>
                  <div className="rounded-xl bg-card border border-border p-4 animate-float" style={{ animationDelay: "0.5s" }}>
                    <div className="text-xs text-muted-foreground mb-1">Fiyat Güncellemesi</div>
                    <div className="text-2xl font-bold">328</div>
                    <div className="text-xs text-accent mt-1">Bugün otomatik</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Floating side cards */}
            <div className="absolute -left-8 top-1/2 -translate-y-1/2 hidden lg:block animate-float-delayed">
              <div className="rounded-xl border border-border bg-card p-4 shadow-xl rotate-[-6deg]">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center">
                    <svg className="w-4 h-4 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                  </div>
                  <span className="text-xs font-medium">Trendyol</span>
                </div>
                <div className="text-lg font-bold">149.90 TL</div>
                <div className="text-xs text-green-500">Optimum fiyat</div>
              </div>
            </div>

            <div className="absolute -right-8 top-1/3 hidden lg:block animate-float">
              <div className="rounded-xl border border-border bg-card p-4 shadow-xl rotate-[6deg]">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
                    <svg className="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <span className="text-xs font-medium">AI Analiz</span>
                </div>
                <div className="text-sm text-muted-foreground">Rakip izleme aktif</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 px-6 bg-secondary/30">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
              Neden OptiPrice AI?
            </h2>
            <p className="mt-4 text-muted-foreground max-w-xl mx-auto">
              E-ticaret operasyonlarınızı tamamen otomatikleştirin
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FeatureCard
              icon={
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
              }
              title="Otomatik Listeleme"
              description="Her platform için AI ile SEO uyumlu başlık, açıklama ve anahtar kelimeler — tek tıkla 3 platformda listeleyin."
              delay={0}
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              }
              title="Otonom Fiyatlama"
              description="Komisyon, kargo, maliyet ve rakip fiyatlarına göre — her platformun ekonomisine özel fiyat stratejisi."
              delay={100}
            />
            <FeatureCard
              icon={
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              }
              title="Canlı Ajan Logları"
              description="Tüm fiyat kararlarını anlık izleyin. Hangi ajan neye karar verdi, neden — tam şeffaflık."
              delay={200}
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
              Nasıl Çalışır?
            </h2>
            <p className="mt-4 text-muted-foreground max-w-xl mx-auto">
              Üç basit adımda e-ticaret otomasyonunuzu başlatın
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <StepCard
              number="1"
              title="Ürününüzü Tanımlayın"
              description="Ürün bilgilerini bir kez girin. AI gerisini halleder."
            />
            <StepCard
              number="2"
              title="Platformları Seçin"
              description="Trendyol, Amazon, kendi siteniz — istediğiniz platformları aktif edin."
            />
            <StepCard
              number="3"
              title="Otonom Yönetim"
              description="AI ajanlarımız 7/24 fiyatları optimize eder, rakipleri izler."
            />
          </div>
        </div>
      </section>

      {/* Platforms marquee */}
      <section id="platforms" className="py-16 border-y border-border overflow-hidden">
        <div className="relative">
          <div className="flex animate-marquee">
            {[...Array(2)].map((_, setIndex) => (
              <div key={setIndex} className="flex items-center gap-16 px-8">
                <PlatformBadge name="Trendyol" />
                <PlatformBadge name="Amazon" />
                <PlatformBadge name="Hepsiburada" />
                <PlatformBadge name="N11" />
                <PlatformBadge name="Shopify" />
                <PlatformBadge name="WooCommerce" />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
            E-ticaretinizi Otomatikleştirin
          </h2>
          <p className="mt-4 text-muted-foreground">
            Tek bir ürün, farklı platformlar, tamamen otonom yönetim.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/auth/register"
              className="rounded-full bg-primary px-8 py-3.5 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity shadow-lg shadow-primary/20"
            >
              Ücretsiz Başlayın
            </Link>
            <Link
              href="/auth/login"
              className="rounded-full border border-border px-8 py-3.5 text-sm font-medium text-foreground hover:bg-secondary transition-colors"
            >
              Giriş Yap
            </Link>
          </div>
        </div>
      </section>

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

function FeatureCard({
  icon,
  title,
  description,
  delay = 0,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  delay?: number;
}) {
  return (
    <div
      className="group rounded-2xl border border-border bg-card p-8 hover:shadow-xl hover:shadow-primary/5 transition-all duration-300 hover:-translate-y-1"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="w-12 h-12 rounded-xl bg-secondary flex items-center justify-center text-foreground mb-5 group-hover:bg-accent group-hover:text-accent-foreground transition-colors">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-foreground">{title}</h3>
      <p className="mt-3 text-sm text-muted-foreground leading-relaxed">{description}</p>
    </div>
  );
}

function StepCard({
  number,
  title,
  description,
}: {
  number: string;
  title: string;
  description: string;
}) {
  return (
    <div className="relative">
      <div className="text-7xl font-bold text-muted/50 mb-4">{number}</div>
      <h3 className="text-xl font-semibold text-foreground">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{description}</p>
    </div>
  );
}

function PlatformBadge({ name }: { name: string }) {
  return (
    <div className="flex-shrink-0 px-6 py-3 rounded-full border border-border bg-card text-sm font-medium text-muted-foreground whitespace-nowrap">
      {name}
    </div>
  );
}
