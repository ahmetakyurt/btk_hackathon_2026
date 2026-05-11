"use server";

import { auth, signOut } from "@/auth";
import { revalidatePath } from "next/cache";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

async function authHeaders(): Promise<HeadersInit> {
  const session = await auth();
  const userId = session?.user?.id;
  return {
    "Content-Type": "application/json",
    ...(userId ? { "X-User-Id": String(userId) } : {}),
  };
}

export type ProfileActionState = { error?: string; ok?: boolean };

export async function updateProfileAction(
  _prev: ProfileActionState,
  formData: FormData,
): Promise<ProfileActionState> {
  const full_name = (formData.get("full_name") as string)?.trim() || null;
  const phone = (formData.get("phone") as string)?.trim() || null;
  const store_name = (formData.get("store_name") as string)?.trim() || null;

  const res = await fetch(`${BACKEND_URL}/api/me`, {
    method: "PATCH",
    headers: await authHeaders(),
    body: JSON.stringify({ full_name, phone, store_name }),
    cache: "no-store",
  });

  if (!res.ok) return { error: "Profil güncellenemedi." };
  revalidatePath("/profile");
  return { ok: true };
}

export async function changePasswordAction(
  _prev: ProfileActionState,
  formData: FormData,
): Promise<ProfileActionState> {
  const current_password = formData.get("current_password") as string;
  const new_password = formData.get("new_password") as string;
  const confirm_password = formData.get("confirm_password") as string;

  if (new_password !== confirm_password) return { error: "Yeni şifreler eşleşmiyor." };
  if (new_password.length < 8) return { error: "Yeni şifre en az 8 karakter olmalı." };

  const res = await fetch(`${BACKEND_URL}/api/me/change-password`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify({ current_password, new_password }),
    cache: "no-store",
  });

  if (res.status === 400) return { error: "Mevcut şifre hatalı." };
  if (!res.ok) return { error: "Şifre değiştirilemedi." };
  return { ok: true };
}

export async function setVacationModeAction(vacation_mode: boolean): Promise<ProfileActionState> {
  const res = await fetch(`${BACKEND_URL}/api/me/vacation-mode`, {
    method: "PATCH",
    headers: await authHeaders(),
    body: JSON.stringify({ vacation_mode }),
    cache: "no-store",
  });
  if (!res.ok) return { error: "Tatil modu güncellenemedi." };
  revalidatePath("/profile");
  return { ok: true };
}

export async function closeAccountAction(): Promise<ProfileActionState> {
  const res = await fetch(`${BACKEND_URL}/api/me`, {
    method: "DELETE",
    headers: await authHeaders(),
    cache: "no-store",
  });
  if (!res.ok) return { error: "Hesap kapatılamadı." };
  await signOut({ redirectTo: "/auth/login" });
  return { ok: true };
}
