import React from "react";
import Link from "next/link";

export default function ImpressumPage() {
  return (
    <main className="min-h-[calc(100vh-3.5rem)] bg-[#0A0E17] px-4 py-12 text-slate-100 sm:px-6 lg:px-8">
      <article className="surface-panel mx-auto max-w-3xl rounded-2xl border border-white/10 bg-[#0F1522] p-6 sm:p-10 space-y-8 text-slate-300">
        <header className="border-b border-white/10 pb-6 space-y-2">
          <p className="text-xs font-semibold text-emerald-400">
            Statutory Legal Notice • Angaben gemäß § 5 DDG
          </p>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            Impressum (Legal Notice)
          </h1>
          <p className="text-sm text-slate-400 leading-relaxed">
            Mandatory operator disclosure under § 5 of the German Digital Services Act (Digitale-Dienste-Gesetz — DDG).
          </p>
        </header>

        <section className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs leading-relaxed text-amber-200">
          <strong className="font-semibold text-amber-100">Pre-Launch Operator Configuration Note:</strong>{" "}
          Replace the bracketed operator fields below with your registered German/EU business address and tax identification before enabling live commercial checkout in Phase S4.
        </section>

        <section className="space-y-3 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            1. Diensteanbieter (Service Operator)
          </h2>
          <div className="rounded-xl border border-white/[0.08] bg-[#0A0E17] p-4 font-mono text-xs space-y-1 text-slate-200" dir="ltr">
            <p>[FOUNDER_LEGAL_NAME]</p>
            <p>[STREET_ADDRESS]</p>
            <p>[POSTAL_CODE_CITY], Deutschland</p>
          </div>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            2. Kontakt (Contact)
          </h2>
          <p>
            E-Mail: <bdi className="font-mono text-slate-100">[CONTACT_EMAIL]</bdi>
          </p>
          <p className="text-xs text-slate-400">
            Electronic inquiries are answered within two business days.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            3. Umsatzsteuer-ID / Steuerliche Angaben (VAT / Tax Status)
          </h2>
          <p>
            Umsatzsteuer-Identifikationsnummer gemäß § 27a Umsatzsteuergesetz (oder Hinweis gem. § 19 UStG):{" "}
            <bdi className="font-mono text-slate-100">[UST_IDNR_OR_KLEINUNTERNEHMER_NOTE]</bdi>
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            4. Hinweis gemäß Rechtsdienstleistungsgesetz (RDG — Non-Legal Service Notice)
          </h2>
          <p>
            FormFlow / AI Form Assistant ist ein rein technisches Sprach-, Übersetzungs- und Ausfüllwerkzeug für Verwaltungs- und Alltagsdokumente. Es wird ausdrücklich <strong className="text-slate-100">keine Rechtsberatung, Steuerberatung oder Einzelfallprüfung im Sinne des Rechtsdienstleistungsgesetzes (RDG)</strong> erbracht. Nutzerinnen und Nutzer prüfen und verantworten sämtliche Angaben vor dem Export und der Einreichung bei Behörden oder Dritten selbst.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            5. Verbraucherstreitbeilegung (§ 36 VSBG)
          </h2>
          <p>
            Wir sind nicht bereit und nicht verpflichtet, an Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle teilzunehmen.
          </p>
        </section>

        <footer className="border-t border-white/10 pt-5 flex flex-wrap gap-4 text-xs font-medium text-emerald-400">
          <Link href="/datenschutz" className="hover:text-emerald-300 hover:underline transition-colors motion-reduce:transition-none">
            Datenschutzerklärung (Privacy Policy)
          </Link>
          <Link href="/agb" className="hover:text-emerald-300 hover:underline transition-colors motion-reduce:transition-none">
            AGB (Terms of Service)
          </Link>
          <Link href="/" className="hover:text-emerald-300 hover:underline transition-colors motion-reduce:transition-none">
            Zur Startseite
          </Link>
        </footer>
      </article>
    </main>
  );
}
