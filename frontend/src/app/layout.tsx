import "./globals.css";
import type { Metadata } from "next";
import { LanguageProvider } from "@/features/form-session/components/LanguageProvider";
import { AuthProvider } from "@/features/auth/context/AuthProvider";
import Navbar from "@/components/Navbar";

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
            <div className="flex min-h-screen flex-col">
              <Navbar />
              <div className="flex-1">{children}</div>
            </div>
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
