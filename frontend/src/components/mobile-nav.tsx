"use client";

import { useState } from "react";
import Link from "next/link";

export function MobileNav() {
  const [open, setOpen] = useState(false);

  return (
    <div className="md:hidden">
      {/* Hamburger button */}
      <button
        onClick={() => setOpen(!open)}
        className="relative w-10 h-10 flex items-center justify-center rounded-lg hover:bg-secondary transition-colors"
        aria-label="Menüyü aç"
      >
        <div className="flex flex-col gap-[5px]">
          <span
            className={`block h-[2px] w-5 bg-foreground transition-all duration-300 ${
              open ? "rotate-45 translate-y-[7px]" : ""
            }`}
          />
          <span
            className={`block h-[2px] w-5 bg-foreground transition-all duration-300 ${
              open ? "opacity-0" : ""
            }`}
          />
          <span
            className={`block h-[2px] w-5 bg-foreground transition-all duration-300 ${
              open ? "-rotate-45 -translate-y-[7px]" : ""
            }`}
          />
        </div>
      </button>

      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Mobile menu panel */}
      <div
        className={`fixed top-16 left-0 right-0 z-50 bg-background/95 backdrop-blur-md border-b border-border shadow-xl transition-all duration-300 ${
          open
            ? "opacity-100 translate-y-0 pointer-events-auto"
            : "opacity-0 -translate-y-2 pointer-events-none"
        }`}
      >
        <div className="px-6 py-5 flex flex-col gap-3">
          <Link
            href="/#features"
            onClick={() => setOpen(false)}
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors py-2"
          >
            Özellikler
          </Link>
          <Link
            href="/#how-it-works"
            onClick={() => setOpen(false)}
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors py-2"
          >
            Nasıl Çalışır
          </Link>
          <Link
            href="/#platforms"
            onClick={() => setOpen(false)}
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors py-2"
          >
            Platformlar
          </Link>
          <Link
            href="/pricing"
            onClick={() => setOpen(false)}
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors py-2"
          >
            Fiyatlandırma
          </Link>

          <div className="border-t border-border my-2" />

          <Link
            href="/auth/login"
            onClick={() => setOpen(false)}
            className="text-sm font-medium text-foreground hover:text-muted-foreground transition-colors py-2"
          >
            Giriş Yap
          </Link>
          <Link
            href="/auth/register"
            onClick={() => setOpen(false)}
            className="rounded-full bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity text-center"
          >
            Hemen Başla
          </Link>
        </div>
      </div>
    </div>
  );
}
