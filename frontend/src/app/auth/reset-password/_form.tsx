"use client";

import { useActionState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { resetPasswordAction, type ActionState } from "../actions";

export default function ResetPasswordForm() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [state, action, pending] = useActionState<ActionState, FormData>(resetPasswordAction, {});

  if (!token) {
    return (
      <div>
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 mb-2">Geçersiz bağlantı</h2>
        <p className="text-sm text-zinc-500">
          Sıfırlama tokenı eksik. Lütfen email&apos;deki bağlantıyı tam olarak kullanın.
        </p>
        <Link
          href="/auth/forgot-password"
          className="mt-4 inline-block text-sm text-zinc-900 dark:text-zinc-100 underline"
        >
          Yeni bağlantı iste
        </Link>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 mb-1">Yeni şifre belirle</h2>
      <p className="text-sm text-zinc-500 mb-5">En az 8 karakter olmalı.</p>

      <form action={action} className="space-y-4">
        <input type="hidden" name="token" value={token} />
        <label className="block">
          <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Yeni şifre</span>
          <input
            name="new_password"
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            className="mt-1 block w-full rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-950 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-100"
          />
        </label>

        {state.error && <p className="text-sm text-red-600">{state.error}</p>}

        <button
          type="submit"
          disabled={pending}
          className="w-full rounded-md bg-zinc-900 text-white py-2.5 text-sm font-medium hover:bg-zinc-800 disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
        >
          {pending ? "Güncelleniyor..." : "Şifremi güncelle"}
        </button>
      </form>
    </div>
  );
}
