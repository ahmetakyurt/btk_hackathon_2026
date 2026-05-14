"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { signOutAction } from "@/app/auth/actions";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/products", label: "Ürünler" },
  { href: "/connections", label: "Platform Bağlantıları" },
  { href: "/logs", label: "Canlı Loglar" },
  { href: "/simulator", label: "Rakip Simülatörü" },
];

export function Sidebar({ userEmail, userName }: { userEmail?: string; userName?: string | null }) {
  const pathname = usePathname();
  if (pathname.startsWith("/auth")) return null;

  return (
    <aside className="w-56 shrink-0 flex flex-col border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 sticky top-0 h-screen overflow-y-auto">
      <div className="px-5 py-5 border-b border-zinc-200 dark:border-zinc-800">
        <span className="text-sm font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          OptiPrice AI
        </span>
        <p className="text-xs text-zinc-400 mt-0.5">Shackathon&apos;26</p>
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
  );
}
