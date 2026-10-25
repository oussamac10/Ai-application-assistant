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
    <div className="fixed top-4 z-50 flex items-center gap-2 text-xs end-4">
      {user ? (
        <>
          <Link
            href="/applications"
            className="btn-secondary px-3 py-1.5 text-xs font-medium"
          >
            {t("myApplications")}
          </Link>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700"
          >
            {t("logout")}
          </button>
        </>
      ) : (
        <>
          <Link
            href="/login"
            className="btn-secondary px-3 py-1.5 text-xs font-medium"
          >
            {t("loginLink")}
          </Link>
          <Link
            href="/register"
            className="btn-primary px-3 py-1.5 text-xs font-semibold"
          >
            {t("registerLink")}
          </Link>
        </>
      )}
    </div>
  );
}
