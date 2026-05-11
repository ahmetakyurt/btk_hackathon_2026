import { Suspense } from "react";
import ResetPasswordForm from "./_form";

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<p className="text-sm text-zinc-500">Yükleniyor...</p>}>
      <ResetPasswordForm />
    </Suspense>
  );
}
