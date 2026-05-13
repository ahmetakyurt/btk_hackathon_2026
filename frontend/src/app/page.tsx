import { auth } from "@/auth";
import { redirect } from "next/navigation";
import Link from "next/link";

export default async function HomePage() {
  const session = await auth();
  if (session?.user) redirect("/dashboard");

  return (
    <div className="min-h-screen flex flex-col bg-zinc-950 text-zinc-50">
      {/* Hero */}
      <section className="flex flex-col items-center justify-center text-center px-6 py-24 flex-1">
        <div className="max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900 px-4 py-1.5 text-xs font-medium text-zinc-400 mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
            Shackathon&apos;26 — BTK × Google × Girvak
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-balance">
            Çok Kanallı{" "}
            <span className="bg-gradient-to-r from-orange-400 via-yellow-400 to-blue-400 bg-clip-text text-transparent">
              Otonom Fiyatlandırma
            </span>{" "}
            Ajanı
          </h1>

          <p className="mt-6 text-lg text-zinc-400 max-w-xl mx-auto text-balance leading-relaxed">
            Ürünlerinizi bir kez tanımlayın. Yapay zeka ajanlarımız her platformda
            (Trendyol, Amazon, kendi siteniz) sizin için listelesin, fiyatlasın ve rakipleri izlesin.
          </p>

          <div className="mt-10 flex items-center justify-center gap-4">
            <Link
              href="/auth/register"
              className="rounded-lg bg-zinc-50 px-6 py-2.5 text-sm font-semibold text-zinc-900 hover:bg-zinc-200 transition-colors"
            >
              Hemen Başla
            </Link>
            <Link
              href="/auth/login"
              className="rounded-lg border border-zinc-700 px-6 py-2.5 text-sm font-medium text-zinc-300 hover:bg-zinc-900 transition-colors"
            >
              Giriş Yap
            </Link>
          </div>
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 max-w-4xl mx-auto mt-20">
          <FeatureCard
            icon="📋"
            title="Otomatik Listeleme"
            description="Her platform için AI ile SEO uyumlu başlık, açıklama ve anahtar kelimeler — tek tıkla 3 platformda listelenin."
          />
          <FeatureCard
            icon="🧠"
            title="Otonom Fiyatlama"
            description="Komisyon, kargo, maliyet ve rakip fiyatlarına göre — her platformun ekonomisine özel fiyat stratejisi."
          />
          <FeatureCard
            icon="📡"
            title="Canlı Ajan Logları"
            description="Tüm fiyat kararlarını anlık izleyin. Hangi ajan neye karar verdi, neden — tam şeffaflık."
          />
        </div>

        {/* Bottom CTA */}
        <p className="mt-16 text-xs text-zinc-500">
          Tek bir ürün, üç ayrı platform, tamamen otonom yönetim.
        </p>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800 px-6 py-8 text-center">
        <p className="text-xs text-zinc-500">
          OptiPrice AI — Shackathon&apos;26 · BTK Akademi × Google × Girvak
        </p>
      </footer>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-6 text-left">
      <div className="text-2xl mb-3">{icon}</div>
      <h3 className="text-sm font-semibold text-zinc-100">{title}</h3>
      <p className="mt-2 text-xs text-zinc-400 leading-relaxed">{description}</p>
    </div>
  );
}
