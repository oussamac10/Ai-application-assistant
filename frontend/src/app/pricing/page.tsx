"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Check,
  Shield,
  HelpCircle,
  ArrowRight,
  Globe2,
  Sparkles,
} from "lucide-react";

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);

  const plans = [
    {
      key: "pilot",
      name: "Free Pilot",
      badge: "Sandbox",
      priceMonthly: "€0",
      priceAnnual: "€0",
      period: "forever",
      description: "For relocation consultants and small agencies testing cross-border candidate intake.",
      features: [
        "Up to 5 candidate cases / month",
        "Worldwide standard templates (Schengen, US, UK, DE)",
        "8-language candidate interview studio",
        "AcroForm PDF autofill with Unicode & RTL",
        "1 Case Manager seat",
      ],
      ctaText: "Start Free Pilot",
      ctaHref: "/portal",
      popular: false,
    },
    {
      key: "agency_pro",
      name: "Agency Pro",
      badge: "Most Popular",
      priceMonthly: "€199",
      priceAnnual: "€159",
      period: "/ month",
      description: "For established immigration law firms, corporate HR teams, and relocation bureaus.",
      features: [
        "100 candidate cases / month",
        "Unlimited case manager & staff seats",
        "1-click Candidate Magic-Link intake",
        "Dual-Pane Verification Studio",
        "Official AcroForm & coordinate PDF overlays",
        "Real-time candidate progress tracking",
        "GDPR Art. 17/20 compliance controls",
        "Priority email & chat support",
      ],
      ctaText: "Upgrade to Pro",
      ctaHref: "/portal",
      popular: true,
    },
    {
      key: "gov_enterprise",
      name: "Enterprise Gov",
      badge: "Municipalities & Gov",
      priceMonthly: "€899",
      priceAnnual: "€749",
      period: "/ month",
      description: "For government authorities, city immigration offices, and global enterprise mobility.",
      features: [
        "1,000 candidate cases / month",
        "Custom municipality form onboarding",
        "Dedicated onboarding manager & custom SLAs",
        "EU data sovereignty & self-hosted option",
        "Custom SSO & SAML 2.0 integration",
        "Audit trail & compliance reporting",
        "Invoice billing (SEPA / Wire Transfer)",
      ],
      ctaText: "Contact Gov Sales",
      ctaHref: "mailto:sales@ai-form-assistant.com?subject=Enterprise%20Gov%20Inquiry",
      popular: false,
    },
  ];

  return (
    <div className="min-h-screen bg-[#0A0E17] text-slate-100 py-16 relative overflow-hidden">
      {/* Subtle top spotlight glow */}
      <div
        className="pointer-events-none absolute inset-x-0 -top-40 h-96 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(16,185,129,0.12),transparent)]"
        aria-hidden="true"
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-16">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <span className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-mono font-semibold bg-[#0F1522] text-slate-300 border border-slate-800">
            <Globe2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Worldwide B2B & B2G Infrastructure</span>
          </span>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight">
            Transparent Pricing for Relocation Agencies & Public Authorities
          </h1>
          <p className="text-base text-slate-400 leading-relaxed">
            Eliminate hours of manual translation and administrative back-and-forth.
            Empower international candidates to complete official forms in their native language.
          </p>

          {/* Billing Toggle */}
          <div className="pt-4 flex items-center justify-center gap-3">
            <span className={`text-xs font-mono font-semibold transition-colors ${!annual ? "text-white" : "text-slate-500"}`}>
              Monthly
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={annual}
              aria-label="Billing frequency toggle"
              onClick={() => setAnnual(!annual)}
              className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0A0E17] motion-reduce:transition-none ${
                annual ? "bg-emerald-500" : "bg-slate-700"
              }`}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200 ease-in-out motion-reduce:transition-none ${
                  annual ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
            <span className={`text-xs font-mono font-semibold flex items-center gap-1.5 transition-colors ${annual ? "text-white" : "text-slate-500"}`}>
              Yearly
              <span className="rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-[10px] px-2 py-0.5 font-mono font-bold">
                Save 20%
              </span>
            </span>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch">
          {plans.map((p) => (
            <div
              key={p.key}
              className={`rounded-2xl p-8 flex flex-col justify-between transition-all duration-200 motion-reduce:transition-none ${
                p.popular
                  ? "relative border-2 border-emerald-500 bg-[#0F1522] shadow-[0_0_35px_-5px_rgba(16,185,129,0.25)]"
                  : "border border-slate-800 bg-[#0F1522] shadow-sm hover:border-slate-700"
              }`}
            >
              {p.popular && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-emerald-500 text-slate-950 text-[10px] font-mono font-extrabold uppercase tracking-wider px-3.5 py-0.5 rounded-full shadow-md flex items-center gap-1">
                  <Sparkles className="w-3 h-3 fill-current" />
                  <span>{p.badge}</span>
                </div>
              )}

              <div className="space-y-6">
                <div>
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white">{p.name}</h2>
                    {!p.popular && (
                      <span className="text-[10px] font-mono font-semibold uppercase text-slate-500 border border-slate-800 bg-[#0A0E17] px-2 py-0.5 rounded">
                        {p.badge}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mt-2 min-h-[32px] leading-relaxed">{p.description}</p>
                </div>

                <div className="flex items-baseline gap-1.5 border-y border-slate-800/80 py-4">
                  <span className="text-4xl font-extrabold text-white tracking-tight font-mono">
                    {annual ? p.priceAnnual : p.priceMonthly}
                  </span>
                  <span className="text-xs text-slate-400 font-mono font-medium">
                    {p.period}
                  </span>
                </div>

                <ul className="space-y-3 pt-1 text-xs text-slate-300">
                  {p.features.map((f, i) => (
                    <li key={i} className="flex items-start gap-2.5">
                      <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="pt-8">
                <Link
                  href={p.ctaHref}
                  className={`w-full py-3 px-4 rounded-xl text-xs font-bold inline-flex items-center justify-center gap-2 transition-all motion-reduce:transition-none ${
                    p.popular
                      ? "btn-primary shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30"
                      : "btn-secondary hover:border-slate-600"
                  }`}
                >
                  {p.ctaText}
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            </div>
          ))}
        </div>

        {/* Enterprise & Security Badges */}
        <div className="rounded-2xl border border-emerald-500/30 bg-gradient-to-r from-[#0F1522] via-[#151D2E] to-[#0F1522] text-white p-8 sm:p-10 shadow-lg flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl text-start">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-emerald-400" />
              <h2 className="text-lg font-bold text-white">Government & Enterprise Security Standards</h2>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Hosted in EU Frankfurt (ISO 27001 certified data centers). Zero training on applicant data,
              strict client data isolation, and 1-click GDPR Art. 17/20 rights.
            </p>
          </div>
          <div className="flex items-center gap-4 shrink-0">
            <Link
              href="/portal"
              className="btn-primary font-bold px-5 py-3 rounded-xl text-xs transition-all shadow-md hover:shadow-lg inline-flex items-center gap-2"
            >
              <span>Open Agency Portal</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="max-w-3xl mx-auto space-y-6 pt-4">
          <div className="text-center space-y-1">
            <h2 className="text-2xl font-bold text-white">Frequently Asked Questions</h2>
            <p className="text-xs text-slate-400">Everything you need to know about our B2B & B2G platform.</p>
          </div>

          <div className="space-y-4 pt-4">
            <div className="p-5 bg-[#0F1522] rounded-2xl border border-slate-800 space-y-2 hover:border-slate-700 transition-colors">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                How does Candidate Magic-Link intake work?
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                When you create a case in the Agency Studio, the platform generates a unique, secure link for your applicant.
                They open the link on mobile or desktop and complete the form in their preferred language (Arabic, English, French, Turkish, etc.) while the platform maps answers directly into the official government PDF fields.
              </p>
            </div>

            <div className="p-5 bg-[#0F1522] rounded-2xl border border-slate-800 space-y-2 hover:border-slate-700 transition-colors">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                Can we add custom forms for our specific city or consulate?
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                Yes. Under Enterprise Gov or custom agency onboarding, we ingest and fingerprint your official PDFs, map all AcroForm widgets and coordinate overlays, and make them available to your case managers immediately.
              </p>
            </div>

            <div className="p-5 bg-[#0F1522] rounded-2xl border border-slate-800 space-y-2 hover:border-slate-700 transition-colors">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                What happens when we reach our monthly quota?
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                Your existing cases remain active and fully accessible. You can upgrade to the next tier or purchase additional case packs right from your Studio dashboard with zero downtime.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
