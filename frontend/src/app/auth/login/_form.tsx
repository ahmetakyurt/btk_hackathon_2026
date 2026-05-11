"use client";

import { useActionState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { loginAction, type ActionState } from "../actions";

export default function LoginForm() {
  const params = useSearchParams();
  const from = params.get("from") ?? "/products";
  const reset = params.get("reset");
  const [state, action, pending] = useActionState<ActionState, FormData>(loginAction, {});

  return (
    <div>
      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 mb-1">Giriş yap</h2>
      <p className="text-sm text-zinc-500 mb-5">OptiPrice AI hesabınızla devam edin.</p>

      {reset === "ok" && (
        <div className="mb-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
          Şifreniz güncellendi. Yeni şifrenizle giriş yapabilirsiniz.
        </div>
      )}

      <form action={action} className="space-y-4">
        <input type="hidden" name="from" value={from} />
        <Field label="Email" name="email" type="email" required autoComplete="email" />
        <Field label="Şifre" name="password" type="password" required autoComplete="current-password" />

        {state.error && (
          <p className="text-sm text-red-600 dark:text-red-400">{state.error}</p>
        )}

        <button
          type="submit"
          disabled={pending}
          className="w-full rounded-md bg-zinc-900 text-white py-2.5 text-sm font-medium hover:bg-zinc-800 disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
        >
          {pending ? "Giriş yapılıyor..." : "Giriş yap"}
        </button>
      </form>

      <div className="mt-5 flex items-center justify-between text-sm text-zinc-500">
        <Link href="/auth/forgot-password" className="hover:text-zinc-900 dark:hover:text-zinc-100">
          Şifremi unuttum
        </Link>
        <Link href="/auth/register" className="hover:text-zinc-900 dark:hover:text-zinc-100">
          Hesap oluştur →
        </Link>
      </div>
    </div>
  );
}

function Field({
  label,
  ...inputProps
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">{label}</span>
      <input
        {...inputProps}
        className="mt-1 block w-full rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-950 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-100"
      />
    </label>
  );
}
