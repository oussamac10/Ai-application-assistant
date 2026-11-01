import "./globals.css";
import type { Metadata } from "next";
import { LanguageProvider } from "@/features/form-session/components/LanguageProvider";
import { AuthProvider } from "@/features/auth/context/AuthProvider";
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
      <body className="min-h-screen bg-[#f8fafc] text-slate-900 antialiased selection:bg-indigo-600/15 selection:text-indigo-900">
        <LanguageProvider>
          <AuthProvider>
            <AppShell>{children}</AppShell>
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
