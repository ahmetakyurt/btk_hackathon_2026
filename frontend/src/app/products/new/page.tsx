"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api, type ProductCreateRequest } from "@/lib/api";
import { useState } from "react";

const schema = z.object({
  sku: z.string().min(1, "SKU zorunlu").max(64),
  title: z.string().min(1, "Ürün adı zorunlu").max(255),
  base_cost: z.coerce.number({ invalid_type_error: "Sayı girin" }).positive("0'dan büyük olmalı"),
  shipping_cost: z.coerce.number({ invalid_type_error: "Sayı girin" }).min(0),
  stock: z.coerce.number({ invalid_type_error: "Sayı girin" }).int().min(0),
  category: z.string().optional(),
  initial_price: z.coerce.number().positive().optional().or(z.literal("")),
});

type FormValues = z.infer<typeof schema>;

export default function NewProductPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { shipping_cost: 0, stock: 0 },
  });

  async function onSubmit(values: FormValues) {
    setSubmitting(true);
    setError(null);
    try {
      const body: ProductCreateRequest = {
        sku: values.sku,
        title: values.title,
        base_cost: values.base_cost,
        shipping_cost: values.shipping_cost,
        stock: values.stock,
        category: values.category || undefined,
        initial_price: values.initial_price || undefined,
      };
      const product = await api<{ id: number }>("/api/products", {
        method: "POST",
        body,
      });
      router.push(`/products/${product.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bir hata oluştu");
      setSubmitting(false);
    }
  }

  return (
    <div className="p-8 max-w-xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Yeni Ürün</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Ürünü kaydettiğinizde AI tüm platformlara otomatik listing oluşturur.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5">
        <Field label="SKU" error={errors.sku?.message}>
          <input {...register("sku")} placeholder="SKU-001" className={inputCls} />
        </Field>

        <Field label="Ürün Adı" error={errors.title?.message}>
          <input {...register("title")} placeholder="Örn: Kablosuz Mouse" className={inputCls} />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Maliyet (₺)" error={errors.base_cost?.message}>
            <input {...register("base_cost")} type="number" step="0.01" placeholder="0.00" className={inputCls} />
          </Field>
          <Field label="Kargo Maliyeti (₺)" error={errors.shipping_cost?.message}>
            <input {...register("shipping_cost")} type="number" step="0.01" placeholder="0.00" className={inputCls} />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Stok" error={errors.stock?.message}>
            <input {...register("stock")} type="number" placeholder="0" className={inputCls} />
          </Field>
          <Field label="Kategori" error={errors.category?.message}>
            <input {...register("category")} placeholder="Elektronik" className={inputCls} />
          </Field>
        </div>

        <Field label="Başlangıç Fiyatı (₺) — opsiyonel" error={errors.initial_price?.message}>
          <input {...register("initial_price")} type="number" step="0.01" placeholder="Boş bırakılırsa maliyet + %30 marj" className={inputCls} />
        </Field>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2">
            {error}
          </p>
        )}

        <div className="flex gap-3 pt-1">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-zinc-900 px-5 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50 transition-colors dark:bg-zinc-50 dark:text-zinc-900"
          >
            {submitting ? "Kaydediliyor…" : "Kaydet & Platformlara Gönder"}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="rounded-md px-5 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-100 transition-colors"
          >
            İptal
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">{label}</label>
      {children}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

const inputCls =
  "rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm text-zinc-900 dark:text-zinc-50 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-zinc-300 transition-shadow";
