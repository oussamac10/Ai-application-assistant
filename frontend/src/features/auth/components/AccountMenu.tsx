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
          <Link
            href="/account"
            className="btn-secondary px-3 py-1.5 text-xs font-medium"
          >
            {t("accountSettings")}
          </Link>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-xl border border-white/[0.12] bg-[#0F1522] px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors motion-reduce:transition-none hover:border-rose-500/40 hover:bg-rose-500/10 hover:text-rose-200 cursor-pointer"
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
