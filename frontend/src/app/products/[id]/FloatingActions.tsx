"use client";

import { useEffect, useState } from "react";

export function FloatingActions() {
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [assistantVisible, setAssistantVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setShowScrollTop(window.scrollY > 300);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const el = document.getElementById("sales-assistant");
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => setAssistantVisible(entry.isIntersecting),
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <>
      {/* Robot butonu — sağ üst köşe, asistan görünürse kaybolur */}
      {!assistantVisible && (
        <button
          type="button"
          onClick={() =>
            document.getElementById("sales-assistant")?.scrollIntoView({ behavior: "smooth" })
          }
          title="Satış Asistanı"
          className="fixed top-4 right-4 z-50 w-10 h-10 rounded-full bg-blue-600 hover:bg-blue-700 shadow-lg flex items-center justify-center text-lg transition-all"
        >
          🤖
        </button>
      )}

      {/* Yukarı çık butonu — aşağı kaydırınca sağ altta belirir */}
      {showScrollTop && (
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          title="Yukarı çık"
          className="fixed bottom-6 right-4 z-50 w-10 h-10 rounded-full bg-zinc-700 hover:bg-zinc-600 shadow-lg flex items-center justify-center text-white text-sm font-bold transition-all"
        >
          ↑
        </button>
      )}
    </>
  );
}
