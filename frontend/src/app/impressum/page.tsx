import React from "react";
import Link from "next/link";

export default function ImpressumPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <article className="surface-panel rounded-2xl p-6 sm:p-10 space-y-8 text-slate-800">
        <header className="border-b border-slate-200 pb-6 space-y-2">
          <p className="text-xs font-semibold text-indigo-700">
            Statutory Legal Notice • Angaben gemäß § 5 DDG
          </p>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
            Impressum (Legal Notice)
          </h1>
          <p className="text-sm text-slate-600 leading-relaxed">
            Mandatory operator disclosure under § 5 of the German Digital Services Act (Digitale-Dienste-Gesetz — DDG).
          </p>
        </header>

        <section className="rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-xs leading-relaxed text-amber-950">
          <strong className="font-semibold">Pre-Launch Operator Configuration Note:</strong>{" "}
          Replace the bracketed operator fields below with your registered German/EU business address and tax identification before enabling live commercial checkout in Phase S4.
        </section>

        <section className="space-y-3 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            1. Diensteanbieter (Service Operator)
          </h2>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 font-mono text-xs space-y-1 text-slate-800" dir="ltr">
            <p>[FOUNDER_LEGAL_NAME]</p>
            <p>[STREET_ADDRESS]</p>
            <p>[POSTAL_CODE_CITY], Deutschland</p>
          </div>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            2. Kontakt (Contact)
          </h2>
          <p>
            E-Mail: <bdi className="font-mono text-slate-900">[CONTACT_EMAIL]</bdi>
          </p>
          <p className="text-xs text-slate-600">
            Electronic inquiries are answered within two business days.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            3. Umsatzsteuer-ID / Steuerliche Angaben (VAT / Tax Status)
          </h2>
          <p>
            Umsatzsteuer-Identifikationsnummer gemäß § 27a Umsatzsteuergesetz (oder Hinweis gem. § 19 UStG):{" "}
            <bdi className="font-mono text-slate-900">[UST_IDNR_OR_KLEINUNTERNEHMER_NOTE]</bdi>
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            4. Hinweis gemäß Rechtsdienstleistungsgesetz (RDG — Non-Legal Service Notice)
          </h2>
          <p>
            FormFlow / AI Form Assistant ist ein rein technisches Sprach-, Übersetzungs- und Ausfüllwerkzeug für Verwaltungs- und Alltagsdokumente. Es wird ausdrücklich <strong>keine Rechtsberatung, Steuerberatung oder Einzelfallprüfung im Sinne des Rechtsdienstleistungsgesetzes (RDG)</strong> erbracht. Nutzerinnen und Nutzer prüfen und verantworten sämtliche Angaben vor dem Export und der Einreichung bei Behörden oder Dritten selbst.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            5. Verbraucherstreitbeilegung (§ 36 VSBG)
          </h2>
          <p>
            Wir sind nicht bereit und nicht verpflichtet, an Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle teilzunehmen.
          </p>
        </section>

        <footer className="border-t border-slate-200 pt-5 flex flex-wrap gap-4 text-xs font-medium text-indigo-700">
          <Link href="/datenschutz" className="hover:underline">
            Datenschutzerklärung (Privacy Policy)
          </Link>
          <Link href="/agb" className="hover:underline">
            AGB (Terms of Service)
          </Link>
          <Link href="/" className="hover:underline">
            Zur Startseite
          </Link>
        </footer>
      </article>
    </main>
  );
}
