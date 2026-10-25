import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
  NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

vi.mock("@/features/document-upload/components/DocumentUploadForm", () => ({
  default: ({ currentLocale }: { currentLocale: string }) => (
    <div data-testid="document-upload-form">
      upload-form locale={currentLocale}
    </div>
  ),
}));

describe("Application landing — Upload Form & language selection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    document.documentElement.lang = "en";
    document.documentElement.dir = "ltr";
  });

  async function renderLanding() {
    const { LanguageProvider } = await import(
      "@/features/form-session/components/LanguageProvider"
    );
    const { default: ApplicationLanding } = await import(
      "@/app/application/page"
    );
    render(
      <LanguageProvider>
        <ApplicationLanding />
      </LanguageProvider>,
    );
  }

  it("renders Upload Form directly without the Select Manually tab", async () => {
    await renderLanding();

    expect(screen.getByTestId("document-upload-form")).toBeDefined();
    expect(screen.getByText(/locale=en/)).toBeDefined();
    expect(screen.queryByRole("button", { name: "tabManual" })).toBeNull();
  });

  it("updates DocumentUploadForm locale when German is selected", async () => {
    await renderLanding();

    fireEvent.click(screen.getByRole("button", { name: "Deutsch" }));
    expect(screen.getByText(/locale=de/)).toBeDefined();
  });

  it("switches document direction to RTL when Arabic is selected", async () => {
    await renderLanding();

    fireEvent.click(screen.getByRole("button", { name: "العربية" }));
    await waitFor(() =>
      expect(document.documentElement).toHaveAttribute("dir", "rtl"),
    );
    expect(screen.getByText(/locale=ar/)).toBeDefined();
  });
});
