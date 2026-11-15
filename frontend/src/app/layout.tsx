import "./globals.css";
import type { Metadata } from "next";
import { LanguageProvider } from "@/features/form-session/components/LanguageProvider";
import { AuthProvider } from "@/features/auth/context/AuthProvider";
import { OrganizationProvider } from "@/features/portal/context/OrganizationContext";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "AI Form Assistant | Multilingual Document & Form Completion",
  description:
    "Understand, normalize, and complete official forms in your preferred language with deterministic validation.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-[#0A0E17] text-slate-100 antialiased selection:bg-emerald-500/20 selection:text-emerald-300">
        <LanguageProvider>
          <AuthProvider>
            <OrganizationProvider>
              <AppShell>{children}</AppShell>
            </OrganizationProvider>
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
