import type { Config } from "tailwindcss";
import plugin from "tailwindcss/plugin";

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
        canvas: "#0A0E17",
        obsidian: {
          950: "#060910",
          900: "#0A0E17",
          850: "#0D131F",
          800: "#0F1522",
          750: "#121A2A",
          700: "#151D2E",
          600: "#1E293B",
          500: "#334155",
          400: "#475569",
        },
        surface: {
          0: "var(--bg-canvas)",
          1: "var(--bg-surface-1)",
          2: "var(--bg-surface-2)",
          3: "var(--bg-surface-3)",
        },
        emerald: {
          300: "#6EE7B7",
          400: "#34D399",
          500: "#10B981",
          600: "#059669",
          700: "#047857",
          800: "#065F46",
          900: "#064E3B",
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
        "2xs": "0 1px 2px 0 rgba(0, 0, 0, 0.4)",
        xs: "0 1px 2px 0 rgba(0, 0, 0, 0.5), 0 1px 3px 0 rgba(0, 0, 0, 0.4)",
        panel: "0 1px 0 0 rgba(255, 255, 255, 0.08) inset, 0 20px 40px -15px rgba(0, 0, 0, 0.7)",
        card: "0 1px 0 0 rgba(255, 255, 255, 0.06) inset, 0 8px 24px -8px rgba(0, 0, 0, 0.6)",
        "btn-primary": "0 1px 0 0 rgba(255, 255, 255, 0.25) inset, 0 2px 8px 0 rgba(16, 185, 129, 0.35)",
        "emerald-glow": "0 0 24px -4px rgba(16, 185, 129, 0.35)",
        "emerald-glow-sm": "0 0 12px -2px rgba(16, 185, 129, 0.25)",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        zoomIn95: {
          "0%": { opacity: "0", transform: "scale(0.95)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        slideInFromBottom: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInFromRight: {
          "0%": { opacity: "0", transform: "translateX(100%)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        slideInFromLeft: {
          "0%": { opacity: "0", transform: "translateX(-100%)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        scaleIn: {
          "0%": { opacity: "0", transform: "scale(0.9)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        pulseGlow: {
          "0%, 100%": { opacity: "1", boxShadow: "0 0 15px rgba(16, 185, 129, 0.45)" },
          "50%": { opacity: "0.6", boxShadow: "0 0 5px rgba(16, 185, 129, 0.15)" },
        },
        laserScan: {
          "0%": { top: "0%", opacity: "0" },
          "15%": { opacity: "1" },
          "85%": { opacity: "1" },
          "100%": { top: "100%", opacity: "0" },
        },
        radarPulse: {
          "0%": { transform: "scale(0.95)", opacity: "0.8" },
          "50%": { transform: "scale(1.1)", opacity: "0.3" },
          "100%": { transform: "scale(1.25)", opacity: "0" },
        },
        glowPulse: {
          "0%, 100%": { opacity: "1", boxShadow: "0 0 20px -3px rgba(16, 185, 129, 0.4)" },
          "50%": { opacity: "0.6", boxShadow: "0 0 8px 0 rgba(16, 185, 129, 0.15)" },
        },
        enter: {
          "0%": {
            opacity: "var(--tw-enter-opacity, 1)",
            transform: "translate3d(var(--tw-enter-translate-x, 0), var(--tw-enter-translate-y, 0), 0) scale3d(var(--tw-enter-scale, 1), var(--tw-enter-scale, 1), var(--tw-enter-scale, 1)) rotate(var(--tw-enter-rotate, 0))",
          },
          "100%": {
            opacity: "1",
            transform: "translate3d(0, 0, 0) scale3d(1, 1, 1) rotate(0)",
          },
        },
        exit: {
          "0%": {
            opacity: "1",
            transform: "translate3d(0, 0, 0) scale3d(1, 1, 1) rotate(0)",
          },
          "100%": {
            opacity: "var(--tw-exit-opacity, 1)",
            transform: "translate3d(var(--tw-exit-translate-x, 0), var(--tw-exit-translate-y, 0), 0) scale3d(var(--tw-exit-scale, 1), var(--tw-exit-scale, 1), var(--tw-exit-scale, 1)) rotate(var(--tw-exit-rotate, 0))",
          },
        },
      },
      animation: {
        "fade-in": "fadeIn 150ms ease-out",
        "zoom-in-95": "zoomIn95 150ms cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-up": "slideInFromBottom 200ms cubic-bezier(0.16, 1, 0.3, 1)",
        "shimmer": "shimmer 2s infinite linear",
        "pulse-glow": "pulseGlow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "laser-scan": "laserScan 3s cubic-bezier(0.4, 0, 0.2, 1) infinite",
        "radar-pulse": "radarPulse 2s cubic-bezier(0, 0, 0.2, 1) infinite",
        "glow-pulse": "glowPulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "scale-in": "scaleIn 150ms cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-in-right": "slideInFromRight 200ms cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-in-left": "slideInFromLeft 200ms cubic-bezier(0.16, 1, 0.3, 1)",
        in: "enter 150ms cubic-bezier(0.16, 1, 0.3, 1)",
        out: "exit 150ms cubic-bezier(0.16, 1, 0.3, 1)",
      },
    },
  },
  plugins: [
    plugin(({ addUtilities }) => {
      addUtilities({
        ".border-hairline": {
          borderColor: "rgba(255, 255, 255, 0.08)",
        },
        ".border-hairline-emerald": {
          borderColor: "rgba(16, 185, 129, 0.25)",
        },
        ".bg-grid-aikido": {
          backgroundImage: `radial-gradient(rgba(255, 255, 255, 0.07) 1px, transparent 1px)`,
          backgroundSize: "24px 24px",
        },
        ".bg-lines-aikido": {
          backgroundImage: `linear-gradient(to right, rgba(255, 255, 255, 0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.04) 1px, transparent 1px)`,
          backgroundSize: "32px 32px",
        },
        ".animate-in": {
          animationName: "enter",
          animationDuration: "150ms",
          animationTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
          "--tw-enter-opacity": "1",
          "--tw-enter-scale": "1",
          "--tw-enter-rotate": "0deg",
          "--tw-enter-translate-x": "0",
          "--tw-enter-translate-y": "0",
        },
        ".animate-out": {
          animationName: "exit",
          animationDuration: "150ms",
          animationTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
          "--tw-exit-opacity": "1",
          "--tw-exit-scale": "1",
          "--tw-exit-rotate": "0deg",
          "--tw-exit-translate-x": "0",
          "--tw-exit-translate-y": "0",
        },
        ".fade-in": { "--tw-enter-opacity": "0" },
        ".fade-in-0": { "--tw-enter-opacity": "0" },
        ".fade-in-50": { "--tw-enter-opacity": "0.5" },
        ".fade-in-100": { "--tw-enter-opacity": "1" },
        ".fade-out": { "--tw-exit-opacity": "0" },
        ".fade-out-0": { "--tw-exit-opacity": "0" },
        ".zoom-in-95": { "--tw-enter-scale": "0.95" },
        ".zoom-in-90": { "--tw-enter-scale": "0.9" },
        ".zoom-in-75": { "--tw-enter-scale": "0.75" },
        ".zoom-in-50": { "--tw-enter-scale": "0.5" },
        ".zoom-in-0": { "--tw-enter-scale": "0" },
        ".zoom-out-95": { "--tw-exit-scale": "0.95" },
        ".zoom-out-90": { "--tw-exit-scale": "0.9" },
        ".slide-in-from-bottom-1": { "--tw-enter-translate-y": "0.25rem" },
        ".slide-in-from-bottom-2": { "--tw-enter-translate-y": "0.5rem" },
        ".slide-in-from-bottom-4": { "--tw-enter-translate-y": "1rem" },
        ".slide-in-from-bottom-8": { "--tw-enter-translate-y": "2rem" },
        ".slide-in-from-top-1": { "--tw-enter-translate-y": "-0.25rem" },
        ".slide-in-from-top-2": { "--tw-enter-translate-y": "-0.5rem" },
        ".slide-in-from-top-4": { "--tw-enter-translate-y": "-1rem" },
        ".slide-in-from-left": { "--tw-enter-translate-x": "-100%" },
        ".slide-in-from-left-2": { "--tw-enter-translate-x": "-0.5rem" },
        ".slide-in-from-left-4": { "--tw-enter-translate-x": "-1rem" },
        ".slide-in-from-right": { "--tw-enter-translate-x": "100%" },
        ".slide-in-from-right-2": { "--tw-enter-translate-x": "0.5rem" },
        ".slide-in-from-right-4": { "--tw-enter-translate-x": "1rem" },
      });
    }),
  ],
};
export default config;
