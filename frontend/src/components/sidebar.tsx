"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/products", label: "Ürünler" },
  { href: "/logs", label: "Canlı Loglar" },
  { href: "/simulator", label: "Rakip Simülatörü" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 flex flex-col border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 min-h-screen">
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
    </aside>
  );
}
