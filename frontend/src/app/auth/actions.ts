"use server";

import { signIn, signOut } from "@/auth";
import { AuthError } from "next-auth";
import { redirect } from "next/navigation";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export type ActionState = { error?: string; ok?: boolean; message?: string };

export async function loginAction(_prev: ActionState, formData: FormData): Promise<ActionState> {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const password = String(formData.get("password") ?? "");
  const from = String(formData.get("from") ?? "/products");

  try {
    await signIn("credentials", { email, password, redirectTo: from || "/products" });
    return { ok: true };
  } catch (err) {
    if (err instanceof AuthError) {
      if (err.type === "CredentialsSignin") return { error: "Email veya şifre hatalı." };
      return { error: "Giriş başarısız. Lütfen tekrar deneyin." };
    }
    throw err;
  }
}

export async function registerAction(_prev: ActionState, formData: FormData): Promise<ActionState> {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const password = String(formData.get("password") ?? "");
  const fullName = String(formData.get("full_name") ?? "").trim() || null;

  if (password.length < 8) return { error: "Şifre en az 8 karakter olmalı." };

  const res = await fetch(`${BACKEND_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
    cache: "no-store",
  });
  if (res.status === 409) return { error: "Bu email zaten kayıtlı." };
  if (!res.ok) return { error: "Kayıt başarısız." };

  // Auto-login after register
  try {
    await signIn("credentials", { email, password, redirectTo: "/products" });
  } catch (err) {
    if (err instanceof AuthError) return { error: "Kayıt başarılı, ancak otomatik giriş yapılamadı." };
    throw err;
  }
  return { ok: true };
}

export async function forgotPasswordAction(
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const res = await fetch(`${BACKEND_URL}/api/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
    cache: "no-store",
  });
  if (!res.ok) return { error: "İstek başarısız. Lütfen tekrar deneyin." };
  return { ok: true, message: "Eğer bu email kayıtlıysa, sıfırlama bağlantısını gönderdik." };
}

export async function resetPasswordAction(
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const token = String(formData.get("token") ?? "");
  const newPassword = String(formData.get("new_password") ?? "");

  if (newPassword.length < 8) return { error: "Şifre en az 8 karakter olmalı." };

  const res = await fetch(`${BACKEND_URL}/api/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: "Geçersiz veya süresi dolmuş bağlantı." }));
    return { error: detail.detail ?? "Sıfırlama başarısız." };
  }
  redirect("/auth/login?reset=ok");
}

export async function signOutAction() {
  await signOut({ redirectTo: "/auth/login" });
}
