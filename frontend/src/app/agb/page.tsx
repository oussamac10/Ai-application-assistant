import React from "react";
import Link from "next/link";

export default function AgbPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <article className="surface-panel rounded-2xl p-6 sm:p-10 space-y-8 text-slate-800">
        <header className="border-b border-slate-200 pb-6 space-y-2">
          <p className="text-xs font-semibold text-indigo-700">
            Terms of Service • Nutzungs- und Geschäftsbedingungen
          </p>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
            Allgemeine Geschäftsbedingungen (AGB)
          </h1>
          <p className="text-sm text-slate-600 leading-relaxed">
            Transparent service boundaries, user verification responsibilities, and usage rules for FormFlow / AI Form Assistant.
          </p>
        </header>

        <section className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-1.5 text-xs leading-relaxed text-slate-700">
          <p className="font-semibold text-slate-900">Key Takeaways in Plain English:</p>
          <p>
            FormFlow helps you read, understand, and transcribe answers onto official forms in your language. <strong>We are not a law firm, tax advisor, immigration consultant, or government office.</strong> We never submit documents on your behalf, and you must verify every field on your exported PDF before signing or submitting it.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            § 1 Leistungsgegenstand (Scope of Service)
          </h2>
          <p>
            FormFlow / AI Form Assistant stellt eine webbasierte Software zur mehrsprachigen Verständnishilfe, deterministischen Formatprüfung (z. B. Datumsangaben, PLZ, IBAN-Prüfziffern) und technischen Befüllung von PDF-Formularen bereit. Eine automatische Übermittlung von Formularen an Behörden, Versicherungen, Vermieter oder sonstige Dritte findet nicht statt.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            § 2 Ausschluss von Rechts- und Steuerberatung (Rechtsdienstleistungsgesetz — RDG)
          </h2>
          <p>
            Die Plattform erbringt <strong>keine Rechtsdienstleistungen im Sinne des § 2 Rechtsdienstleistungsgesetz (RDG)</strong> sowie keine Steuer-, Sozialversicherungs- oder Migrationsberatung. Bereitgestellte Feldhinweise und Checklisten dienen ausschließlich der allgemeinen sprachlichen und organisatorischen Orientierung und ersetzen keine fachkundige Beratung im Einzelfall.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            § 3 Eigenverantwortliche Endkontrolle durch Nutzerinnen und Nutzer
          </h2>
          <p>
            Automatisierte Texterkennung (OCR), Übersetzungen und Feldzuordnungen können insbesondere bei gescannten Dokumenten Abweichungen aufweisen. Nutzerinnen und Nutzer sind verpflichtet, sämtliche eingetragenen Werte im Zwei-Spalten-Prüfstudio sowie im exportierten PDF-Dokument vor der Unterzeichnung und Einreichung vollständig auf Richtigkeit und Vollständigkeit zu kontrollieren.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            § 4 Faire Nutzung, Seitenlimits &amp; Digitale Dokumentenpässe
          </h2>
          <p>
            Zur Sicherstellung stabiler Antwortzeiten gelten technische Schutzgrenzen (maximal 10 MB Dateigröße bzw. 20 Seiten pro Dokument sowie Sitzungs-Kontingente). Kostenlose Sitzungen ermöglichen die geführte Beantwortung und eine mit Wasserzeichen versehene PDF-Vorschau. Bei Einführung kostenpflichtiger Einzel-Dokumentenpässe oder Pakete werden Bruttopreise inklusive gesetzlicher Umsatzsteuer sowie gesetzliche Widerrufshinweise für digitale Inhalte (§ 356 Abs. 5 BGB) vor jedem Kaufabschluss transparent ausgewiesen.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            § 5 Haftung und Anwendbares Recht
          </h2>
          <p>
            Wir haften unbeschränkt bei Vorsatz, grober Fahrlässigkeit sowie bei Verletzung von Leben, Körper oder Gesundheit. Bei leicht fahrlässiger Verletzung wesentlicher Vertragspflichten ist die Haftung auf den vertragstypischen, vorhersehbaren Schaden begrenzt. Es gilt das Recht der Bundesrepublik Deutschland unter Beachtung zwingender Verbraucherschutzvorschriften Ihres gewöhnlichen Aufenthaltsstaates innerhalb der Europäischen Union.
          </p>
        </section>

        <footer className="border-t border-slate-200 pt-5 flex flex-wrap gap-4 text-xs font-medium text-indigo-700">
          <Link href="/impressum" className="hover:underline">
            Impressum
          </Link>
          <Link href="/datenschutz" className="hover:underline">
            Datenschutzerklärung (Privacy Policy)
          </Link>
          <Link href="/" className="hover:underline">
            Zur Startseite
          </Link>
        </footer>
      </article>
    </main>
  );
}
