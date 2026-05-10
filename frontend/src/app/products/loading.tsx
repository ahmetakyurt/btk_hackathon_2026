export default function ProductsLoading() {
  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div className="h-7 w-24 bg-zinc-200 dark:bg-zinc-800 rounded animate-pulse" />
        <div className="h-9 w-28 bg-zinc-200 dark:bg-zinc-800 rounded-md animate-pulse" />
      </div>
      <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 overflow-hidden bg-white dark:bg-zinc-900">
        <div className="bg-zinc-50 dark:bg-zinc-800 px-4 py-3 flex gap-8">
          {["w-12", "w-32", "w-20", "w-16", "w-12", "w-24"].map((w, i) => (
            <div key={i} className={`h-4 ${w} bg-zinc-200 dark:bg-zinc-700 rounded animate-pulse`} />
          ))}
        </div>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="px-4 py-3 flex gap-8 border-t border-zinc-100 dark:border-zinc-800">
            {["w-16", "w-40", "w-24", "w-12", "w-8", "w-28"].map((w, j) => (
              <div key={j} className={`h-4 ${w} bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse`} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
