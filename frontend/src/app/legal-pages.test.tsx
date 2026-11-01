import React from "react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LanguageProvider } from "@/features/form-session/components/LanguageProvider";
import Footer from "@/components/Footer";
import ImpressumPage from "@/app/impressum/page";
import DatenschutzPage from "@/app/datenschutz/page";
import AgbPage from "@/app/agb/page";

describe("Phase S3 — German Legal Compliance Pages & Global Footer", () => {
  it("renders Footer with RDG non-legal disclaimer and links to /impressum, /datenschutz, /agb", () => {
    render(
      <LanguageProvider>
        <Footer />
      </LanguageProvider>,
    );

    expect(screen.getByRole("link", { name: /Impressum/i })).toHaveAttribute("href", "/impressum");
    expect(screen.getByRole("link", { name: /Datenschutz/i })).toHaveAttribute(
      "href",
      "/datenschutz",
    );
    expect(screen.getByRole("link", { name: /AGB/i })).toHaveAttribute("href", "/agb");
    expect(screen.getByText(/RDG/i)).toBeInTheDocument();
  });

  it("renders /impressum with § 5 DDG statutory disclosures and explicit operator placeholders", () => {
    render(
      <LanguageProvider>
        <ImpressumPage />
      </LanguageProvider>,
    );

    expect(screen.getByRole("heading", { level: 1, name: /Impressum/i })).toBeInTheDocument();
    expect(screen.getAllByText(/§ 5 DDG/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/\[FOUNDER_LEGAL_NAME\]/)).toBeInTheDocument();
    expect(screen.getAllByText(/Rechtsdienstleistungsgesetz/i).length).toBeGreaterThan(0);
  });

  it("renders /datenschutz with GDPR Art. 13/14, 24h anonymous auto-purge, and Art. 17/20 rights", () => {
    render(
      <LanguageProvider>
        <DatenschutzPage />
      </LanguageProvider>,
    );

    expect(
      screen.getByRole("heading", { level: 1, name: /Datenschutzerklärung/i }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Art\. 17 DSGVO/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Art\. 20 DSGVO/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/24/).length).toBeGreaterThan(0);
  });

  it("renders /agb with explicit RDG non-legal scope and user verification duty", () => {
    render(
      <LanguageProvider>
        <AgbPage />
      </LanguageProvider>,
    );

    expect(
      screen.getByRole("heading", { level: 1, name: /Allgemeine Geschäftsbedingungen/i }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Rechtsdienstleistungsgesetz/i).length).toBeGreaterThan(0);
  });
});
