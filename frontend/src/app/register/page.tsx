import React, { Suspense } from "react";
import RegisterForm from "@/features/auth/components/RegisterForm";

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-[50vh] flex items-center justify-center p-8 text-xs text-slate-400">Loading...</div>}>
      <RegisterForm />
    </Suspense>
  );
}
