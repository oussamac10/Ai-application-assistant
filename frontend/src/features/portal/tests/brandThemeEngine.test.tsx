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
const setPreviewThemeConfigMock = vi.fn();

vi.mock("../context/OrganizationContext", () => ({
  useOrganization: () => ({
    organization: null,
    loading: false,
    refreshOrganization: refreshOrganizationMock,
    effectiveThemeConfig: null,
    setPreviewThemeConfig: setPreviewThemeConfigMock,
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

describe("System-Panel Scoped Brand Theme Engine", () => {
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

  it("applies, hydrates, and resets brand variables strictly on [data-system-panel='true'] without mutating :root", () => {
    render(
      <>
        <div data-testid="public-site">Public Homepage</div>
        <div data-testid="system-panel" data-system-panel="true">
          System Panel
        </div>
      </>,
    );

    const publicSite = screen.getByTestId("public-site");
    const systemPanel = screen.getByTestId("system-panel");

    applyBrandThemeToDocument(
      { primary_color: "#FEDB00", accent_color: "#0F172A" },
      { persist: true },
    );

    const storedRaw = window.localStorage.getItem(BRAND_THEME_STORAGE_KEY);
    expect(storedRaw).toBeTruthy();

    // Public website & documentElement must never receive custom brand overrides
    expect(
      document.documentElement.style.getPropertyValue("--brand-500-rgb"),
    ).toBe("");
    expect(document.documentElement.hasAttribute("data-brand-custom")).toBe(
      false,
    );
    expect(publicSite.style.getPropertyValue("--brand-500-rgb")).toBe("");

    // Only the system panel container receives the chosen brand color
    expect(systemPanel.dataset.brandCustom).toBe("true");
    expect(systemPanel.style.getPropertyValue("--brand-500-rgb")).toBe(
      "254 219 0",
    );

    systemPanel.style.removeProperty("--brand-500-rgb");
    systemPanel.dataset.brandCustom = "false";

    hydratePersistedBrandTheme();
    expect(systemPanel.dataset.brandCustom).toBe("true");
    expect(systemPanel.style.getPropertyValue("--brand-500-rgb")).toBe(
      "254 219 0",
    );
    expect(
      document.documentElement.style.getPropertyValue("--brand-500-rgb"),
    ).toBe("");

    clearPersistedBrandTheme();
    expect(window.localStorage.getItem(BRAND_THEME_STORAGE_KEY)).toBeNull();
    expect(systemPanel.dataset.brandCustom).toBe("false");
    expect(systemPanel.style.getPropertyValue("--brand-500-rgb")).toBe(
      "16 185 129",
    );
  });

  it("live-previews, saves, and reverts unsaved colors strictly inside [data-system-panel='true']", async () => {
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
      <div data-testid="system-panel" data-system-panel="true">
        <OrganizationSettings initialOrg={baseOrg} onOrgUpdated={onOrgUpdated} />
      </div>,
    );

    const systemPanel = screen.getByTestId("system-panel");

    fireEvent.click(
      screen.getByRole("button", { name: /Layout & Appearance/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: /Sovereign Gold/i }));

    await waitFor(() => {
      expect(systemPanel.style.getPropertyValue("--brand-500-rgb")).toBe(
        "254 219 0",
      );
      expect(setPreviewThemeConfigMock).toHaveBeenCalledWith(
        expect.objectContaining({ primary_color: "#FEDB00" }),
      );
    });
    expect(
      document.documentElement.style.getPropertyValue("--brand-500-rgb"),
    ).toBe("");

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

    const { rerender } = render(
      <div data-testid="system-panel-unsaved" data-system-panel="true">
        <OrganizationSettings initialOrg={baseOrg} onOrgUpdated={vi.fn()} />
      </div>,
    );

    const unsavedPanel = screen.getByTestId("system-panel-unsaved");

    fireEvent.click(
      screen.getByRole("button", { name: /Layout & Appearance/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: /Sovereign Gold/i }));

    await waitFor(() => {
      expect(unsavedPanel.style.getPropertyValue("--brand-500-rgb")).toBe(
        "254 219 0",
      );
    });

    setPreviewThemeConfigMock.mockClear();
    rerender(<div data-testid="system-panel-unsaved" data-system-panel="true" />);

    expect(setPreviewThemeConfigMock).toHaveBeenCalledWith(null);
    expect(unsavedPanel.style.getPropertyValue("--brand-500-rgb")).toBe(
      "16 185 129",
    );
  });
});
