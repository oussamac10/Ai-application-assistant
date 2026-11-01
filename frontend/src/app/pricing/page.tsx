"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Check,
  Shield,
  Zap,
  Building,
  HelpCircle,
  ArrowRight,
  Globe2,
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
    <div className="min-h-screen bg-slate-50/50 py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-16">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
            <Globe2 className="w-3.5 h-3.5" />
            Worldwide B2B & B2G Infrastructure
          </span>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 tracking-tight">
            Transparent Pricing for Relocation Agencies & Public Authorities
          </h1>
          <p className="text-base text-slate-600 leading-relaxed">
            Eliminate hours of manual translation and administrative back-and-forth.
            Empower international candidates to complete official forms in their native language.
          </p>

          {/* Billing Toggle */}
          <div className="pt-4 flex items-center justify-center gap-3">
            <span className={`text-xs font-semibold ${!annual ? "text-slate-900" : "text-slate-500"}`}>
              Monthly
            </span>
            <button
              type="button"
              onClick={() => setAnnual(!annual)}
              className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                annual ? "bg-indigo-600" : "bg-slate-300"
              }`}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition duration-200 ease-in-out ${
                  annual ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
            <span className={`text-xs font-semibold flex items-center gap-1.5 ${annual ? "text-slate-900" : "text-slate-500"}`}>
              Yearly
              <span className="rounded-full bg-emerald-100 text-emerald-800 text-[10px] px-2 py-0.5 font-bold">
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
              className={`rounded-3xl p-8 flex flex-col justify-between transition-all duration-200 bg-white ${
                p.popular
                  ? "border-2 border-indigo-600 shadow-xl relative"
                  : "border border-slate-200 shadow-sm"
              }`}
            >
              {p.popular && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-indigo-600 text-white text-[11px] font-bold uppercase tracking-wider px-3.5 py-1 rounded-full shadow-sm">
                  {p.badge}
                </div>
              )}

              <div className="space-y-6">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">{p.name}</h2>
                  <p className="text-xs text-slate-500 mt-1 min-h-[32px]">{p.description}</p>
                </div>

                <div className="flex items-baseline gap-1.5">
                  <span className="text-4xl font-extrabold text-slate-900 tracking-tight">
                    {annual ? p.priceAnnual : p.priceMonthly}
                  </span>
                  <span className="text-xs text-slate-500 font-medium">
                    {p.period}
                  </span>
                </div>

                <ul className="space-y-3 pt-2 text-xs text-slate-600">
                  {p.features.map((f, i) => (
                    <li key={i} className="flex items-start gap-2.5">
                      <Check className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="pt-8">
                <Link
                  href={p.ctaHref}
                  className={`w-full py-3 px-4 rounded-xl text-xs font-bold inline-flex items-center justify-center gap-2 transition-all ${
                    p.popular
                      ? "btn-primary shadow-md hover:shadow-lg"
                      : "btn-secondary"
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
        <div className="rounded-3xl bg-indigo-900 text-white p-8 sm:p-10 shadow-lg flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl text-start">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-indigo-300" />
              <h2 className="text-lg font-bold">Government & Enterprise Security Standards</h2>
            </div>
            <p className="text-xs text-indigo-200 leading-relaxed">
              Hosted in EU Frankfurt (ISO 27001 certified data centers). Zero training on applicant data,
              strict client data isolation, and 1-click GDPR Art. 17/20 rights.
            </p>
          </div>
          <div className="flex items-center gap-4 shrink-0">
            <Link
              href="/portal"
              className="bg-white text-indigo-900 hover:bg-indigo-50 font-bold px-5 py-3 rounded-xl text-xs transition-colors"
            >
              Open Agency Portal
            </Link>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="max-w-3xl mx-auto space-y-6 pt-4">
          <div className="text-center space-y-1">
            <h2 className="text-2xl font-bold text-slate-900">Frequently Asked Questions</h2>
            <p className="text-xs text-slate-500">Everything you need to know about our B2B & B2G platform.</p>
          </div>

          <div className="space-y-4 pt-4">
            <div className="p-5 bg-white rounded-2xl border border-slate-200 space-y-2">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-indigo-600" />
                How does Candidate Magic-Link intake work?
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                When you create a case in the Agency Studio, the platform generates a unique, secure link for your applicant.
                They open the link on mobile or desktop and complete the form in their preferred language (Arabic, English, French, Turkish, etc.) while the platform maps answers directly into the official government PDF fields.
              </p>
            </div>

            <div className="p-5 bg-white rounded-2xl border border-slate-200 space-y-2">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-indigo-600" />
                Can we add custom forms for our specific city or consulate?
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Yes. Under Enterprise Gov or custom agency onboarding, we ingest and fingerprint your official PDFs, map all AcroForm widgets and coordinate overlays, and make them available to your case managers immediately.
              </p>
            </div>

            <div className="p-5 bg-white rounded-2xl border border-slate-200 space-y-2">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-indigo-600" />
                What happens when we reach our monthly quota?
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed">
                Your existing cases remain active and fully accessible. You can upgrade to the next tier or purchase additional case packs right from your Studio dashboard with zero downtime.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
