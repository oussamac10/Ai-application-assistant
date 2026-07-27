import "./globals.css";
import type { Metadata } from "next";
import { LanguageProvider } from "@/features/form-session/components/LanguageProvider";
import { AuthProvider } from "@/features/auth/context/AuthProvider";
import AccountMenu from "@/features/auth/components/AccountMenu";

export const metadata: Metadata = {
  title: "AI Form Assistant",
  description: "Multilingual AI Form Assistant Project Foundation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <LanguageProvider>
          <AuthProvider>
            <AccountMenu />
            {children}
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
