"use client";

import { useActionState } from "react";
import Link from "next/link";
import { forgotPasswordAction, type ActionState } from "../actions";

export default function ForgotPasswordPage() {
  const [state, action, pending] = useActionState<ActionState, FormData>(forgotPasswordAction, {});

  return (
    <div>
      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 mb-1">Şifremi unuttum</h2>
      <p className="text-sm text-zinc-500 mb-5">
        Hesabınıza bağlı email adresini girin, sıfırlama bağlantısını gönderelim.
      </p>

      {state.ok ? (
        <div className="rounded-md border border-green-200 bg-green-50 px-3 py-3 text-sm text-green-800">
          {state.message}
        </div>
      ) : (
        <form action={action} className="space-y-4">
          <label className="block">
            <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Email</span>
            <input
              name="email"
              type="email"
              required
              autoComplete="email"
              className="mt-1 block w-full rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-950 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-100"
            />
          </label>

          {state.error && <p className="text-sm text-red-600">{state.error}</p>}

          <button
            type="submit"
            disabled={pending}
            className="w-full rounded-md bg-zinc-900 text-white py-2.5 text-sm font-medium hover:bg-zinc-800 disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
          >
            {pending ? "Gönderiliyor..." : "Sıfırlama bağlantısı gönder"}
          </button>
        </form>
      )}

      <p className="mt-5 text-sm text-zinc-500">
        <Link href="/auth/login" className="hover:text-zinc-900 dark:hover:text-zinc-100">
          ← Giriş sayfasına dön
        </Link>
      </p>
    </div>
  );
}
