import { Logo } from "@/components/logo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen w-full flex flex-col bg-background">
      {/* Logo header */}
      <header className="fixed top-0 left-0 right-0 z-50 px-6 py-4">
        <Logo size="md" linkToHome={true} />
      </header>

      {/* Auth content */}
      <div className="flex-1 flex items-center justify-center p-4 pt-20">
        <div className="w-full max-w-md">
          <div className="rounded-2xl border border-border bg-card p-8 shadow-xl shadow-primary/5">
            {children}
          </div>
          <p className="mt-6 text-center text-xs text-muted-foreground">
            OptiPrice AI — Çok kanallı dinamik fiyatlandırma
          </p>
        </div>
      </div>
    </div>
  );
}
