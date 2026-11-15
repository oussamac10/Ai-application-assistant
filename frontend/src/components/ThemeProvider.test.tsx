import React from "react";
import { beforeEach, describe, expect, it } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import en from "../../messages/en.json";
import { STORAGE_KEY, ThemeProvider, useTheme } from "./ThemeProvider";
import ThemeToggle from "./ThemeToggle";

function ThemeProbe() {
  const { theme } = useTheme();
  return <span data-testid="active-theme">{theme}</span>;
}

function renderWithProviders(ui: React.ReactNode) {
  return render(
    <NextIntlClientProvider locale="en" messages={en} timeZone="UTC">
      <ThemeProvider>{ui}</ThemeProvider>
    </NextIntlClientProvider>,
  );
}

describe("Dual-Theme System — ThemeProvider & ThemeToggle", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.classList.remove("light", "dark");
    delete document.documentElement.dataset.theme;
    document.documentElement.style.colorScheme = "";
  });

  it("defaults to dark mode on initial mount when localStorage is empty", async () => {
    renderWithProviders(<ThemeProbe />);

    await waitFor(() => {
      expect(screen.getByTestId("active-theme")).toHaveTextContent("dark");
    });
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.classList.contains("light")).toBe(false);
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(document.documentElement.style.colorScheme).toBe("dark");
  });

  it("toggles between dark and light mode via icon ThemeToggle and persists to localStorage", async () => {
    renderWithProviders(
      <>
        <ThemeProbe />
        <ThemeToggle variant="icon" />
      </>,
    );

    const toLightBtn = await screen.findByRole("button", { name: "Switch to light mode" });
    fireEvent.click(toLightBtn);

    expect(screen.getByTestId("active-theme")).toHaveTextContent("light");
    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(document.documentElement.style.colorScheme).toBe("light");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("light");

    const toDarkBtn = screen.getByRole("button", { name: "Switch to dark mode" });
    fireEvent.click(toDarkBtn);

    expect(screen.getByTestId("active-theme")).toHaveTextContent("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.classList.contains("light")).toBe(false);
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("dark");
  });

  it("hydrates directly into light mode when persisted in localStorage", async () => {
    window.localStorage.setItem(STORAGE_KEY, "light");

    renderWithProviders(<ThemeProbe />);

    await waitFor(() => {
      expect(screen.getByTestId("active-theme")).toHaveTextContent("light");
    });
    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("updates aria-pressed and switches modes correctly in pill variant", async () => {
    renderWithProviders(
      <>
        <ThemeProbe />
        <ThemeToggle variant="pill" />
      </>,
    );

    const darkBtn = await screen.findByRole("button", { name: "Dark" });
    const lightBtn = screen.getByRole("button", { name: "Light" });

    expect(darkBtn).toHaveAttribute("aria-pressed", "true");
    expect(lightBtn).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(lightBtn);

    expect(screen.getByTestId("active-theme")).toHaveTextContent("light");
    expect(darkBtn).toHaveAttribute("aria-pressed", "false");
    expect(lightBtn).toHaveAttribute("aria-pressed", "true");
    expect(document.documentElement.classList.contains("light")).toBe(true);

    fireEvent.click(darkBtn);

    expect(screen.getByTestId("active-theme")).toHaveTextContent("dark");
    expect(darkBtn).toHaveAttribute("aria-pressed", "true");
    expect(lightBtn).toHaveAttribute("aria-pressed", "false");
  });
});
