"use client";

import { useActionState } from "react";
import Link from "next/link";
import { registerAction, type ActionState } from "../actions";

export default function RegisterPage() {
  const [state, action, pending] = useActionState<ActionState, FormData>(registerAction, {});

  return (
    <div>
      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 mb-1">Hesap oluştur</h2>
      <p className="text-sm text-zinc-500 mb-5">Birkaç saniyede başlayın.</p>

      <form action={action} className="space-y-4">
        <Field label="Ad Soyad (opsiyonel)" name="full_name" type="text" autoComplete="name" />
        <Field label="Email" name="email" type="email" required autoComplete="email" />
        <Field
          label="Şifre (en az 8 karakter)"
          name="password"
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
        />

        {state.error && (
          <p className="text-sm text-red-600 dark:text-red-400">{state.error}</p>
        )}

        <button
          type="submit"
          disabled={pending}
          className="w-full rounded-md bg-zinc-900 text-white py-2.5 text-sm font-medium hover:bg-zinc-800 disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
        >
          {pending ? "Hesap oluşturuluyor..." : "Hesap oluştur"}
        </button>
      </form>

      <p className="mt-5 text-sm text-zinc-500">
        Zaten hesabınız var mı?{" "}
        <Link href="/auth/login" className="text-zinc-900 dark:text-zinc-100 underline">
          Giriş yap
        </Link>
      </p>
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
