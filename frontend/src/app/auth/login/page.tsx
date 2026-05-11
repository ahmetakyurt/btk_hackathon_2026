import { Suspense } from "react";
import LoginForm from "./_form";

export default function LoginPage() {
  return (
    <Suspense fallback={<p className="text-sm text-zinc-500">Yükleniyor...</p>}>
      <LoginForm />
    </Suspense>
  );
}
