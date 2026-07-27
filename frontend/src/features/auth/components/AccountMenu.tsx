"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useAuth } from "../context/AuthProvider";

export default function AccountMenu() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const t = useTranslations("auth");

  if (loading) {
    return null;
  }

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  return (
    <div className="fixed top-4 z-50 flex items-center gap-3 text-sm end-4">
      {user ? (
        <>
          <Link
            href="/applications"
            className="rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 font-semibold text-slate-200 backdrop-blur transition hover:border-slate-600"
          >
            {t("myApplications")}
          </Link>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 font-semibold text-slate-300 backdrop-blur transition hover:border-rose-700 hover:text-rose-300"
          >
            {t("logout")}
          </button>
        </>
      ) : (
        <>
          <Link
            href="/login"
            className="rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 font-semibold text-slate-200 backdrop-blur transition hover:border-slate-600"
          >
            {t("loginLink")}
          </Link>
          <Link
            href="/register"
            className="rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-500 px-3 py-2 font-semibold text-white shadow-lg shadow-indigo-500/20 transition hover:opacity-95"
          >
            {t("registerLink")}
          </Link>
        </>
      )}
    </div>
  );
}
