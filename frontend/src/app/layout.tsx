import "./globals.css";
import type { Metadata } from "next";
import { LanguageProvider } from "@/features/form-session/components/LanguageProvider";
import { ThemeProvider } from "@/components/ThemeProvider";
import { AuthProvider } from "@/features/auth/context/AuthProvider";
import { OrganizationProvider } from "@/features/portal/context/OrganizationContext";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "AI Form Assistant | Fill Out Official Forms in Your Language",
  description:
    "Read official PDFs in your own language, answer simple guided questions, and download cleanly filled forms.",
};

const themeInitScript = `(function(){try{var t=localStorage.getItem("formflow-theme");var m=t==="light"?"light":"dark";var d=document.documentElement;d.classList.remove("light","dark");d.classList.add(m);d.dataset.theme=m;d.style.colorScheme=m;var b=localStorage.getItem("formflow-brand-theme");if(b){var p=JSON.parse(b);if(p&&p.vars){for(var k in p.vars){if(Object.prototype.hasOwnProperty.call(p.vars,k)&&k.indexOf("--brand-")===0){d.style.setProperty(k,p.vars[k]);}}d.dataset.brandCustom="true";}}}catch(e){}})();`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" data-theme="dark" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-screen bg-[#0A0E17] text-slate-100 antialiased selection:bg-emerald-500/20 selection:text-emerald-300">
        <LanguageProvider>
          <ThemeProvider>
            <AuthProvider>
              <OrganizationProvider>
                <AppShell>{children}</AppShell>
              </OrganizationProvider>
            </AuthProvider>
          </ThemeProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
