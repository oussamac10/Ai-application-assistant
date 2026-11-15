"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

export type ThemeMode = "dark" | "light";
export const STORAGE_KEY = "formflow-theme";

interface ThemeContextValue {
  theme: ThemeMode;
  setTheme: (mode: ThemeMode) => void;
  toggleTheme: () => void;
}

/** Synchronizes theme class, data attribute, and color-scheme on the root element. */
export function applyThemeToDocument(mode: ThemeMode): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.toggle("light", mode === "light");
  root.classList.toggle("dark", mode === "dark");
  root.dataset.theme = mode;
  root.style.colorScheme = mode;
}

function safeWriteStorage(mode: ThemeMode): void {
  try {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, mode);
    }
  } catch {
    // Ignore storage quota or privacy-mode errors
  }
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "dark",
  setTheme: (mode: ThemeMode) => {
    applyThemeToDocument(mode);
    safeWriteStorage(mode);
  },
  toggleTheme: () => {
    if (typeof document === "undefined") return;
    const next: ThemeMode = document.documentElement.classList.contains("light") ? "dark" : "light";
    applyThemeToDocument(next);
    safeWriteStorage(next);
  },
});

/** Provides persistent Dark (Aikido Obsidian) and Light theme state across the application. */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>("dark");

  useEffect(() => {
    let initial: ThemeMode = "dark";
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved === "light" || saved === "dark") {
        initial = saved;
      } else if (document.documentElement.classList.contains("light")) {
        initial = "light";
      }
    } catch {
      if (document.documentElement.classList.contains("light")) {
        initial = "light";
      }
    }
    setThemeState(initial);
    applyThemeToDocument(initial);
  }, []);

  const setTheme = useCallback((mode: ThemeMode) => {
    setThemeState(mode);
    safeWriteStorage(mode);
    applyThemeToDocument(mode);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const next: ThemeMode = prev === "dark" ? "light" : "dark";
      safeWriteStorage(next);
      applyThemeToDocument(next);
      return next;
    });
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

/** Returns the active application theme mode and theme mutators. */
export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}
