import React, { Suspense } from "react";
import LoginForm from "@/features/auth/components/LoginForm";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-[50vh] flex items-center justify-center p-8 text-xs text-slate-400">Loading...</div>}>
      <LoginForm />
    </Suspense>
  );
}
