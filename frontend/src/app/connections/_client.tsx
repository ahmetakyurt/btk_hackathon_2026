"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { cn } from "@/lib/utils";
import type { PlatformConnection } from "@/lib/api";

// ─── Platform definitions ────────────────────────────────────────────────────

interface PlatformDef {
  code: string;
  name: string;
  icon: string;
  fields: { id: "seller_id" | "api_key"; label: string; placeholder: string }[];
}

const PLATFORMS: PlatformDef[] = [
  {
    code: "trendyol",
    name: "Trendyol",
    icon: "🛒",
    fields: [
      { id: "seller_id", label: "Seller ID", placeholder: "12345678" },
      { id: "api_key", label: "API Key", placeholder: "abc123..." },
    ],
  },
  {
    code: "amazon",
    name: "Amazon",
    icon: "📦",
    fields: [
      { id: "seller_id", label: "Seller ID", placeholder: "AXXXXXXXXXXXX" },
      { id: "api_key", label: "MWS / SP-API Key", placeholder: "Amzn..." },
    ],
  },
  {
    code: "own_site",
    name: "Kendi Mağazam",
    icon: "🏪",
    fields: [
      { id: "seller_id", label: "Store URL", placeholder: "https://mystore.com" },
    ],
  },
];

// ─── Form schema ─────────────────────────────────────────────────────────────

const formSchema = z.object({
  seller_id: z.string().min(1, "Bu alan zorunlu"),
  api_key: z.string().optional(),
});
type FormValues = z.infer<typeof formSchema>;

// ─── Component ───────────────────────────────────────────────────────────────

export function ConnectionsClient({
  initialConnections,
}: {
  initialConnections: PlatformConnection[];
}) {
  const [connections, setConnections] = useState<PlatformConnection[]>(initialConnections);
  const [openForm, setOpenForm] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<Record<string, boolean>>({});

  function getConn(code: string) {
    return connections.find((c) => c.platform_code === code) ?? null;
  }

  function setPlatformBusy(code: string, val: boolean) {
    setBusy((prev) => ({ ...prev, [code]: val }));
  }

  async function handleDisconnect(conn: PlatformConnection) {
    setPlatformBusy(conn.platform_code, true);
    try {
      const res = await fetch(`/api/proxy/api/connections/${conn.platform_id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error(await res.text());
      setConnections((prev) => prev.filter((c) => c.platform_id !== conn.platform_id));
      setTestResults((prev) => {
        const n = { ...prev };
        delete n[conn.platform_code];
        return n;
      });
    } catch (err) {
      alert(err instanceof Error ? err.message : "Bir hata oluştu");
    } finally {
      setPlatformBusy(conn.platform_code, false);
    }
  }

  async function handleTest(conn: PlatformConnection) {
    setPlatformBusy(conn.platform_code, true);
    setTestResults((prev) => ({ ...prev, [conn.platform_code]: "" }));
    try {
      const res = await fetch(`/api/proxy/api/connections/${conn.platform_id}/test`, {
        method: "POST",
      });
      const data = (await res.json()) as { ok: boolean; store_name: string };
      setTestResults((prev) => ({
        ...prev,
        [conn.platform_code]: data.ok ? `✓ ${data.store_name}` : "Test başarısız",
      }));
    } catch {
      setTestResults((prev) => ({ ...prev, [conn.platform_code]: "Test başarısız" }));
    } finally {
      setPlatformBusy(conn.platform_code, false);
    }
  }

  return (
    <div className="p-8 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
          Platform Bağlantıları
        </h1>
        <p className="text-sm text-zinc-500 mt-1">
          Ürün eklemek için en az bir platform hesabı bağlayın.
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {PLATFORMS.map((def) => {
          const conn = getConn(def.code);
          const isConnected = conn !== null;
          const isBusy = busy[def.code] ?? false;
          const testMsg = testResults[def.code];

          return (
            <div
              key={def.code}
              className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-5"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{def.icon}</span>
                  <div>
                    <div className="font-medium text-zinc-900 dark:text-zinc-50">{def.name}</div>
                    {isConnected && (
                      <div className="text-xs text-zinc-400 mt-0.5">
                        Seller: {conn.seller_id ?? "—"} · Bağlandı:{" "}
                        {new Date(conn.connected_at).toLocaleDateString("tr-TR")}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
                      isConnected
                        ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400"
                        : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
                    )}
                  >
                    <span
                      className={cn(
                        "h-1.5 w-1.5 rounded-full",
                        isConnected ? "bg-green-500" : "bg-zinc-400"
                      )}
                    />
                    {isConnected ? "Bağlı" : "Bağlı Değil"}
                  </span>

                  {isConnected ? (
                    <>
                      <button
                        type="button"
                        disabled={isBusy}
                        onClick={() => handleTest(conn)}
                        className="rounded-md border border-zinc-300 dark:border-zinc-700 px-3 py-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 disabled:opacity-50 transition-colors"
                      >
                        {isBusy ? "…" : "Test Et"}
                      </button>
                      <button
                        type="button"
                        disabled={isBusy}
                        onClick={() => handleDisconnect(conn)}
                        className="rounded-md border border-red-200 dark:border-red-800 px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 transition-colors"
                      >
                        Kes
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setOpenForm(openForm === def.code ? null : def.code)}
                      className="rounded-md bg-zinc-900 dark:bg-zinc-50 px-3 py-1.5 text-xs font-medium text-white dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors"
                    >
                      Bağlan
                    </button>
                  )}
                </div>
              </div>

              {testMsg && (
                <p
                  className={cn(
                    "mt-3 text-xs rounded-md px-3 py-2",
                    testMsg.startsWith("✓")
                      ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                      : "bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400"
                  )}
                >
                  {testMsg}
                </p>
              )}

              {!isConnected && openForm === def.code && (
                <ConnectForm
                  def={def}
                  onConnected={(newConn) => {
                    setConnections((prev) => [...prev, newConn]);
                    setOpenForm(null);
                  }}
                  onCancel={() => setOpenForm(null)}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Connect form ─────────────────────────────────────────────────────────────

function ConnectForm({
  def,
  onConnected,
  onCancel,
}: {
  def: PlatformDef;
  onConnected: (conn: PlatformConnection) => void;
  onCancel: () => void;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(formSchema) });
  const [serverError, setServerError] = useState<string | null>(null);

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      const res = await fetch("/api/proxy/api/connections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform_code: def.code,
          seller_id: values.seller_id,
          api_key: values.api_key || undefined,
        }),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(data?.detail ?? `${res.status} ${res.statusText}`);
      }
      const conn = (await res.json()) as PlatformConnection;
      onConnected(conn);
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Bir hata oluştu");
    }
  }

  const inputCls =
    "rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm text-zinc-900 dark:text-zinc-50 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-300 transition-shadow w-full";

  return (
    <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSubmit(onSubmit)(e);
        }}
        className="flex flex-col gap-3"
      >
        {def.fields.map((field) => (
          <div key={field.id} className="flex flex-col gap-1">
            <label className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
              {field.label}
            </label>
            <input
              {...register(field.id)}
              placeholder={field.placeholder}
              className={inputCls}
              type={field.id === "api_key" ? "password" : "text"}
            />
            {errors[field.id] && (
              <p className="text-xs text-red-600">{errors[field.id]?.message}</p>
            )}
          </div>
        ))}

        {serverError && (
          <p className="text-xs text-red-600 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md px-3 py-2">
            {serverError}
          </p>
        )}

        <div className="flex gap-2 pt-1">
          <button
            type="button"
            onClick={handleSubmit(onSubmit)}
            disabled={isSubmitting}
            className="rounded-md bg-zinc-900 dark:bg-zinc-50 px-4 py-1.5 text-sm font-medium text-white dark:text-zinc-900 hover:bg-zinc-700 disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? "Bağlanıyor…" : "Bağla"}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md px-4 py-1.5 text-sm font-medium text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          >
            İptal
          </button>
        </div>
      </form>
    </div>
  );
}
