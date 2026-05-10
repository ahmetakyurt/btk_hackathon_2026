export default function ProductDetailLoading() {
  return (
    <div className="p-8">
      <div className="h-4 w-16 bg-zinc-200 dark:bg-zinc-800 rounded animate-pulse mb-6" />
      <div className="h-6 w-64 bg-zinc-200 dark:bg-zinc-800 rounded animate-pulse mb-1" />
      <div className="h-3 w-24 bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse mb-6" />

      <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-5 mb-6 grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i}>
            <div className="h-3 w-12 bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse mb-1" />
            <div className="h-5 w-20 bg-zinc-200 dark:bg-zinc-700 rounded animate-pulse" />
          </div>
        ))}
      </div>

      <div className="h-4 w-32 bg-zinc-200 dark:bg-zinc-800 rounded animate-pulse mb-3" />
      <div className="grid grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-100 dark:border-zinc-800 flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-zinc-200 dark:bg-zinc-700 animate-pulse" />
              <div className="h-4 w-20 bg-zinc-200 dark:bg-zinc-700 rounded animate-pulse flex-1" />
              <div className="h-5 w-16 bg-zinc-100 dark:bg-zinc-800 rounded-full animate-pulse" />
            </div>
            <div className="px-4 py-3 flex flex-col gap-2">
              {Array.from({ length: 4 }).map((_, j) => (
                <div key={j} className="flex justify-between">
                  <div className="h-3 w-16 bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse" />
                  <div className="h-3 w-20 bg-zinc-200 dark:bg-zinc-700 rounded animate-pulse" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
