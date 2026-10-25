import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Plus Jakarta Sans", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        background: "var(--bg-canvas)",
        foreground: "var(--text-primary)",
        surface: {
          0: "var(--bg-canvas)",
          1: "var(--bg-surface-1)",
          2: "var(--bg-surface-2)",
          3: "var(--bg-surface-3)",
        },
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
        },
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255, 255, 255, 0.05) inset, 0 20px 40px -15px rgba(0, 0, 0, 0.55)",
        card: "0 1px 0 0 rgba(255, 255, 255, 0.04) inset, 0 8px 24px -8px rgba(0, 0, 0, 0.4)",
        "btn-primary": "0 1px 0 0 rgba(255, 255, 255, 0.18) inset, 0 1px 2px 0 rgba(0, 0, 0, 0.35)",
      },
    },
  },
  plugins: [],
};
export default config;
