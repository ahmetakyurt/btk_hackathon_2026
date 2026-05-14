"use client";

import { useState, useRef, useEffect } from "react";

const SUGGESTED_QUESTIONS = [
  "Bu ürünü neden bu fiyatta tuttun?",
  "Hangi platformda en çok kâr ediyoruz?",
  "Buybox'ı geri almak için ne yapmam gerekiyor?",
  "Floor fiyatına neden yaklaştık?",
];

interface Message {
  role: "user" | "assistant";
  text: string;
}

export function SalesAssistant({ productId }: { productId: number }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(question: string) {
    if (!question.trim() || loading) return;
    const userMsg: Message = { role: "user", text: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`/api/proxy/api/products/${productId}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: data.answer ?? "Yanıt alınamadı." },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Bir hata oluştu. Lütfen tekrar deneyin." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-8">
      <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-4">
        Satış Asistanı
        <span className="ml-2 text-[10px] font-normal text-zinc-400 align-middle">
          Gemini ile güçlendirildi
        </span>
      </h2>

      <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden">
        {/* Chat area */}
        <div className="min-h-[180px] max-h-[340px] overflow-y-auto px-4 py-4 flex flex-col gap-3">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full py-6 gap-3">
              <span className="text-2xl">🤖</span>
              <p className="text-xs text-zinc-400 text-center max-w-xs">
                Bu ürünün fiyatlandırma kararları hakkında Türkçe soru sorabilirsiniz.
              </p>
              {/* Suggested questions */}
              <div className="flex flex-wrap gap-1.5 justify-center mt-1">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => send(q)}
                    disabled={loading}
                    className="text-[11px] px-2.5 py-1 rounded-full border border-zinc-200 dark:border-zinc-700 text-zinc-500 dark:text-zinc-400 hover:border-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "assistant" && (
                <span className="text-sm shrink-0 mt-0.5">🤖</span>
              )}
              <div
                className={`max-w-[80%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-br-sm"
                    : "bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 rounded-bl-sm"
                }`}
              >
                {msg.text}
              </div>
              {msg.role === "user" && (
                <span className="text-sm shrink-0 mt-0.5">👤</span>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-2 justify-start">
              <span className="text-sm">🤖</span>
              <div className="bg-zinc-100 dark:bg-zinc-800 rounded-xl rounded-bl-sm px-3 py-2">
                <div className="flex gap-1 items-center h-4">
                  <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-zinc-100 dark:border-zinc-800 px-3 py-2.5 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(input)}
            placeholder="Ürün hakkında bir şey sor..."
            disabled={loading}
            className="flex-1 text-xs bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-zinc-800 dark:text-zinc-200 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            type="button"
            onClick={() => send(input)}
            disabled={!input.trim() || loading}
            className="shrink-0 text-xs px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-lg transition-colors font-medium"
          >
            Sor
          </button>
        </div>
      </div>
    </div>
  );
}
