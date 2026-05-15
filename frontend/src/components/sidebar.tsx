"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { signOutAction } from "@/app/auth/actions";
import { Logo } from "@/components/logo";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/products", label: "Ürünler" },
  { href: "/connections", label: "Platform Bağlantıları" },
  { href: "/logs", label: "Canlı Loglar" },
  { href: "/simulator", label: "Rakip Simülatörü" },
  { href: "/plan", label: "Planım" },
];

export function Sidebar({ userEmail, userName }: { userEmail?: string; userName?: string | null }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close mobile sidebar on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // Prevent body scroll when mobile sidebar is open
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  if (pathname.startsWith("/auth")) return null;

  return (
    <>
      {/* Mobile hamburger button — fixed top-left */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="md:hidden fixed top-3 left-3 z-[60] w-10 h-10 flex items-center justify-center rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
        aria-label="Menüyü aç"
      >
        <div className="flex flex-col gap-[5px]">
          <span
            className={`block h-[2px] w-5 bg-zinc-700 dark:bg-zinc-300 transition-all duration-300 ${
              mobileOpen ? "rotate-45 translate-y-[7px]" : ""
            }`}
          />
          <span
            className={`block h-[2px] w-5 bg-zinc-700 dark:bg-zinc-300 transition-all duration-300 ${
              mobileOpen ? "opacity-0" : ""
            }`}
          />
          <span
            className={`block h-[2px] w-5 bg-zinc-700 dark:bg-zinc-300 transition-all duration-300 ${
              mobileOpen ? "-rotate-45 -translate-y-[7px]" : ""
            }`}
          />
        </div>
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-[49] bg-black/30 backdrop-blur-sm"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar — desktop: always visible, mobile: slide-in overlay */}
      <aside
        className={cn(
          "w-56 shrink-0 flex flex-col border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 h-screen overflow-y-auto",
          // Desktop: static sidebar
          "hidden md:flex md:sticky md:top-0",
          // Mobile: fixed overlay sidebar
          mobileOpen && "!flex fixed top-0 left-0 z-[55] shadow-2xl"
        )}
      >
        <div className="px-5 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <Logo size="sm" linkToHome={false} />
          <p className="text-xs text-zinc-400 mt-1.5">Hackathon&apos;26</p>
        </div>
        <nav className="flex flex-col gap-0.5 px-3 py-4 flex-1">
          {NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                pathname.startsWith(href)
                  ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                  : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-50"
              )}
            >
              {label}
            </Link>
          ))}
        </nav>

        {userEmail && (
          <div className="border-t border-zinc-200 dark:border-zinc-800 px-4 py-3">
            <Link
              href="/profile"
              className="block group"
            >
              <div className="text-xs font-medium text-zinc-700 dark:text-zinc-200 truncate group-hover:text-zinc-900 dark:group-hover:text-zinc-50 transition-colors">
                {userName || userEmail}
              </div>
              {userName && (
                <div className="text-[11px] text-zinc-400 truncate">{userEmail}</div>
              )}
            </Link>
            <form action={signOutAction} className="mt-2">
              <button
                type="submit"
                className="w-full text-left text-xs text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
              >
                Çıkış yap →
              </button>
            </form>
          </div>
        )}
      </aside>
    </>
  );
}
