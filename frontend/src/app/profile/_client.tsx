"use client";

import { useActionState, useTransition, useState } from "react";
import {
  updateProfileAction,
  changePasswordAction,
  setVacationModeAction,
  closeAccountAction,
  type ProfileActionState,
} from "./actions";

export interface ProfileData {
  id: number;
  email: string;
  full_name: string | null;
  phone: string | null;
  store_name: string | null;
  vacation_mode: boolean;
  created_at: string;
  total_products: number;
  active_listings: number;
  buybox_count: number;
  price_updates_24h: number;
}

// ─── Avatar ───────────────────────────────────────────────────────────────────

const AVATAR_COLORS = [
  "bg-blue-500", "bg-violet-500", "bg-emerald-500", "bg-orange-500",
  "bg-pink-500", "bg-teal-500", "bg-indigo-500", "bg-rose-500",
];

function Avatar({ name, email }: { name: string | null; email: string }) {
  const initials = name
    ? name.split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 2)
    : email[0].toUpperCase();
  const color = AVATAR_COLORS[email.charCodeAt(0) % AVATAR_COLORS.length];
  return (
    <div
      className={`${color} w-16 h-16 rounded-full flex items-center justify-center text-white text-xl font-bold shrink-0`}
    >
      {initials}
    </div>
  );
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-5 py-4">
      <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">{value}</p>
      <p className="text-xs text-zinc-500 mt-0.5">{label}</p>
    </div>
  );
}

// ─── Section wrapper ──────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-6">
      <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50 mb-5">{title}</h2>
      {children}
    </section>
  );
}

function Field({
  label,
  name,
  type = "text",
  defaultValue,
  placeholder,
  required,
  minLength,
  autoComplete,
}: {
  label: string;
  name: string;
  type?: string;
  defaultValue?: string;
  placeholder?: string;
  required?: boolean;
  minLength?: number;
  autoComplete?: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">{label}</span>
      <input
        name={name}
        type={type}
        defaultValue={defaultValue}
        placeholder={placeholder}
        required={required}
        minLength={minLength}
        autoComplete={autoComplete}
        className="mt-1 block w-full rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-950 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-100"
      />
    </label>
  );
}

function SuccessBanner({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
      {message}
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return <p className="text-sm text-red-600">{message}</p>;
}

// ─── Profile form ─────────────────────────────────────────────────────────────

function ProfileForm({ profile }: { profile: ProfileData }) {
  const [state, action, pending] = useActionState<ProfileActionState, FormData>(
    updateProfileAction,
    {},
  );
  return (
    <form action={action} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field
          label="Ad Soyad"
          name="full_name"
          defaultValue={profile.full_name ?? ""}
          placeholder="Ad Soyad"
          autoComplete="name"
        />
        <Field
          label="Mağaza Adı"
          name="store_name"
          defaultValue={profile.store_name ?? ""}
          placeholder="Mağazanızın adı"
        />
        <div>
          <label className="block">
            <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">Email</span>
            <input
              type="email"
              value={profile.email}
              disabled
              className="mt-1 block w-full rounded-md border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 px-3 py-2 text-sm text-zinc-400 cursor-not-allowed"
            />
          </label>
        </div>
        <Field
          label="Telefon"
          name="phone"
          type="tel"
          defaultValue={profile.phone ?? ""}
          placeholder="+90 5xx xxx xx xx"
          autoComplete="tel"
        />
      </div>
      {state.ok && <SuccessBanner message="Profil başarıyla güncellendi." />}
      {state.error && <ErrorBanner message={state.error} />}
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-zinc-900 text-white px-4 py-2 text-sm font-medium hover:bg-zinc-800 disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
      >
        {pending ? "Kaydediliyor..." : "Değişiklikleri Kaydet"}
      </button>
    </form>
  );
}

// ─── Password form ────────────────────────────────────────────────────────────

function PasswordForm() {
  const [state, action, pending] = useActionState<ProfileActionState, FormData>(
    changePasswordAction,
    {},
  );
  return (
    <form action={action} className="space-y-4 max-w-sm">
      <Field
        label="Mevcut Şifre"
        name="current_password"
        type="password"
        required
        autoComplete="current-password"
      />
      <Field
        label="Yeni Şifre"
        name="new_password"
        type="password"
        required
        minLength={8}
        autoComplete="new-password"
      />
      <Field
        label="Yeni Şifre Tekrar"
        name="confirm_password"
        type="password"
        required
        minLength={8}
        autoComplete="new-password"
      />
      {state.ok && <SuccessBanner message="Şifreniz güncellendi." />}
      {state.error && <ErrorBanner message={state.error} />}
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-zinc-900 text-white px-4 py-2 text-sm font-medium hover:bg-zinc-800 disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
      >
        {pending ? "Güncelleniyor..." : "Şifreyi Güncelle"}
      </button>
    </form>
  );
}

// ─── Account section ──────────────────────────────────────────────────────────

function AccountSection({ vacationMode }: { vacationMode: boolean }) {
  const [isPending, startTransition] = useTransition();
  const [vacMode, setVacMode] = useState(vacationMode);
  const [vacError, setVacError] = useState<string>();
  const [showConfirm, setShowConfirm] = useState(false);
  const [deleteError, setDeleteError] = useState<string>();
  const [deleteLoading, setDeleteLoading] = useState(false);

  function handleVacationToggle() {
    startTransition(async () => {
      const result = await setVacationModeAction(!vacMode);
      if (result.error) {
        setVacError(result.error);
      } else {
        setVacMode((v) => !v);
        setVacError(undefined);
      }
    });
  }

  async function handleDeleteAccount() {
    setDeleteLoading(true);
    const result = await closeAccountAction();
    if (result.error) {
      setDeleteError(result.error);
      setDeleteLoading(false);
    }
    // on success, signOut redirect fires in the server action
  }

  return (
    <div className="space-y-6">
      {/* Vacation mode */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-zinc-900 dark:text-zinc-50">Tatil Modu</p>
          <p className="text-xs text-zinc-500 mt-0.5">
            Aktifken mağazanız geçici olarak duraklatılmış olarak işaretlenir.
          </p>
          {vacError && <p className="text-xs text-red-600 mt-1">{vacError}</p>}
        </div>
        <button
          type="button"
          onClick={handleVacationToggle}
          disabled={isPending}
          className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none disabled:opacity-60 ${
            vacMode ? "bg-zinc-900 dark:bg-zinc-100" : "bg-zinc-200 dark:bg-zinc-700"
          }`}
          role="switch"
          aria-checked={vacMode}
        >
          <span
            className={`inline-block h-5 w-5 transform rounded-full bg-white dark:bg-zinc-900 shadow transition-transform ${
              vacMode ? "translate-x-5" : "translate-x-0"
            }`}
          />
        </button>
      </div>

      {/* Delete account */}
      <div className="border-t border-zinc-200 dark:border-zinc-800 pt-5">
        <p className="text-sm font-medium text-red-600 mb-1">Hesabı Kapat</p>
        <p className="text-xs text-zinc-500 mb-3">
          Hesabınız devre dışı bırakılır. Bu işlem geri alınamaz.
        </p>
        {deleteError && <p className="text-xs text-red-600 mb-2">{deleteError}</p>}
        {!showConfirm ? (
          <button
            type="button"
            onClick={() => setShowConfirm(true)}
            className="rounded-md border border-red-300 text-red-600 px-4 py-2 text-sm font-medium hover:bg-red-50 dark:hover:bg-red-950"
          >
            Hesabı Kapat
          </button>
        ) : (
          <div className="flex gap-2 items-center">
            <span className="text-xs text-zinc-600 dark:text-zinc-400">Emin misiniz?</span>
            <button
              type="button"
              onClick={handleDeleteAccount}
              disabled={deleteLoading}
              className="rounded-md bg-red-600 text-white px-4 py-2 text-sm font-medium hover:bg-red-700 disabled:opacity-60"
            >
              {deleteLoading ? "İşleniyor..." : "Evet, Hesabımı Kapat"}
            </button>
            <button
              type="button"
              onClick={() => setShowConfirm(false)}
              className="rounded-md border border-zinc-300 dark:border-zinc-700 text-zinc-600 dark:text-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-50 dark:hover:bg-zinc-800"
            >
              İptal
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main client component ────────────────────────────────────────────────────

export function ProfileClient({ profile }: { profile: ProfileData }) {
  const memberSince = new Date(profile.created_at).toLocaleDateString("tr-TR", {
    year: "numeric",
    month: "long",
  });

  return (
    <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Avatar name={profile.full_name} email={profile.email} />
        <div>
          <h1 className="text-lg font-bold text-zinc-900 dark:text-zinc-50">
            {profile.store_name || profile.full_name || profile.email}
          </h1>
          <p className="text-sm text-zinc-500">{profile.email}</p>
          <p className="text-xs text-zinc-400 mt-0.5">{memberSince} tarihinden beri üye</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Toplam Ürün" value={profile.total_products} />
        <StatCard label="Aktif Listing" value={profile.active_listings} />
        <StatCard label="Buybox Kazanılan" value={profile.buybox_count} />
        <StatCard label="Fiyat Güncelleme (24s)" value={profile.price_updates_24h} />
      </div>

      {/* Profile info */}
      <Section title="Profil Bilgileri">
        <ProfileForm profile={profile} />
      </Section>

      {/* Password */}
      <Section title="Güvenlik & Şifre">
        <PasswordForm />
      </Section>

      {/* Account */}
      <Section title="Hesap Durumu & İşlemler">
        <AccountSection vacationMode={profile.vacation_mode} />
      </Section>
    </div>
  );
}
