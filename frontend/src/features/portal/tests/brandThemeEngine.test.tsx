import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { OrganizationSettings } from "../components/OrganizationSettings";
import * as portalClient from "../services/portalClient";
import { Organization } from "../types";
import {
  BRAND_THEME_STORAGE_KEY,
  DEFAULT_THEME_CONFIG,
  POPULAR_AUTHORITY_PALETTES,
  RgbColor,
  applyBrandThemeToDocument,
  clearPersistedBrandTheme,
  generateBrandCssVariables,
  getContrastRatio,
  hydratePersistedBrandTheme,
} from "../utils/theme";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const refreshOrganizationMock = vi.fn().mockResolvedValue(undefined);

vi.mock("../context/OrganizationContext", () => ({
  useOrganization: () => ({
    organization: null,
    loading: false,
    refreshOrganization: refreshOrganizationMock,
  }),
}));

function parseChannels(value: string): RgbColor {
  const [r, g, b] = value.trim().split(/\s+/).map(Number);
  return { r, g, b };
}

const WHITE: RgbColor = { r: 255, g: 255, b: 255 };
const DARK_CARD_BG: RgbColor = { r: 15, g: 21, b: 34 }; // #0F1522

const baseOrg: Organization = {
  id: "org-theme-1",
  name: "Stadtverwaltung Stuttgart",
  slug: "stadt-stuttgart",
  billing_plan: "government",
  allowed_cases_per_month: 200,
  role: "owner",
  created_at: "2026-11-01T00:00:00Z",
  verification_status: "verified_official",
  is_verified_government: true,
  supported_languages: ["de", "en", "fr"],
};

describe("Dynamic Authority Brand Theme Engine", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    clearPersistedBrandTheme();
  });

  afterEach(() => {
    window.localStorage.clear();
    clearPersistedBrandTheme();
  });

  it("generates WCAG 2.2 AA Light & Dark contrast variables for all 8 authority palettes", () => {
    const sovereignGold = POPULAR_AUTHORITY_PALETTES.find(
      (p) => p.name === "Sovereign Gold",
    );
    expect(sovereignGold).toBeDefined();
    const goldVars = generateBrandCssVariables({
      primary_color: sovereignGold!.primary,
      accent_color: sovereignGold!.accent,
    });
    expect(goldVars["--brand-500-rgb"]).toBe("254 219 0");

    for (const palette of POPULAR_AUTHORITY_PALETTES) {
      const vars = generateBrandCssVariables({
        primary_color: palette.primary,
        accent_color: palette.accent,
      });

      const lightTextContrast = getContrastRatio(
        parseChannels(vars["--brand-700-rgb"]),
        WHITE,
      );
      const darkTextContrast = getContrastRatio(
        parseChannels(vars["--brand-400-rgb"]),
        DARK_CARD_BG,
      );
      const lightBorderContrast = getContrastRatio(
        parseChannels(vars["--brand-border-light-rgb"]),
        WHITE,
      );

      expect(lightTextContrast).toBeGreaterThanOrEqual(4.5);
      expect(darkTextContrast).toBeGreaterThanOrEqual(4.5);
      expect(lightBorderContrast).toBeGreaterThanOrEqual(3.0);
    }

    expect(
      generateBrandCssVariables({ primary_color: "#FEDB00" })["--brand-on-solid"],
    ).toBe("#0f172a");
    expect(
      generateBrandCssVariables({ primary_color: "#10B981" })["--brand-on-solid"],
    ).toBe("#0f172a");
    expect(
      generateBrandCssVariables({ primary_color: "#1E3A8A" })["--brand-on-solid"],
    ).toBe("#ffffff");
    expect(
      generateBrandCssVariables({ primary_color: "#E11D48" })["--brand-on-solid"],
    ).toBe("#ffffff");
  });

  it("persists, hydrates, and clears brand CSS variables on documentElement", () => {
    applyBrandThemeToDocument(
      { primary_color: "#FEDB00", accent_color: "#0F172A" },
      { persist: true },
    );

    const storedRaw = window.localStorage.getItem(BRAND_THEME_STORAGE_KEY);
    expect(storedRaw).toBeTruthy();
    expect(document.documentElement.dataset.brandCustom).toBe("true");
    expect(
      document.documentElement.style.getPropertyValue("--brand-500-rgb"),
    ).toBe("254 219 0");

    document.documentElement.style.removeProperty("--brand-500-rgb");
    document.documentElement.dataset.brandCustom = "false";

    hydratePersistedBrandTheme();
    expect(document.documentElement.dataset.brandCustom).toBe("true");
    expect(
      document.documentElement.style.getPropertyValue("--brand-500-rgb"),
    ).toBe("254 219 0");

    clearPersistedBrandTheme();
    expect(window.localStorage.getItem(BRAND_THEME_STORAGE_KEY)).toBeNull();
    expect(document.documentElement.dataset.brandCustom).toBe("false");
    expect(
      document.documentElement.style.getPropertyValue("--brand-500-rgb"),
    ).toBe("16 185 129");
  });

  it("live-previews, saves, and reverts unsaved brand colors in OrganizationSettings", async () => {
    const updatedOrg: Organization = {
      ...baseOrg,
      ui_theme_config: {
        ...DEFAULT_THEME_CONFIG,
        primary_color: "#FEDB00",
        accent_color: "#0F172A",
      },
    };
    const updateSpy = vi
      .spyOn(portalClient, "updateOrganizationProfile")
      .mockResolvedValue(updatedOrg);
    const onOrgUpdated = vi.fn();

    const { unmount: unmountSaved } = render(
      <OrganizationSettings initialOrg={baseOrg} onOrgUpdated={onOrgUpdated} />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: /Layout & Appearance/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: /Sovereign Gold/i }));

    await waitFor(() => {
      expect(
        document.documentElement.style.getPropertyValue("--brand-500-rgb"),
      ).toBe("254 219 0");
    });

    fireEvent.click(screen.getByRole("button", { name: /Save Colors/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          ui_theme_config: expect.objectContaining({
            primary_color: "#FEDB00",
            accent_color: "#0F172A",
          }),
        }),
      );
      expect(onOrgUpdated).toHaveBeenCalledWith(updatedOrg);
      expect(refreshOrganizationMock).toHaveBeenCalled();
    });

    unmountSaved();
    clearPersistedBrandTheme();

    const { unmount: unmountUnsaved } = render(
      <OrganizationSettings initialOrg={baseOrg} onOrgUpdated={vi.fn()} />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: /Layout & Appearance/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: /Sovereign Gold/i }));

    await waitFor(() => {
      expect(
        document.documentElement.style.getPropertyValue("--brand-500-rgb"),
      ).toBe("254 219 0");
    });

    unmountUnsaved();

    expect(
      document.documentElement.style.getPropertyValue("--brand-500-rgb"),
    ).toBe("16 185 129");
  });
});
