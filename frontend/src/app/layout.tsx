import "./globals.css";
import type { Metadata } from "next";

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
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
