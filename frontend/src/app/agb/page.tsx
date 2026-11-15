import React from "react";
import Link from "next/link";

export default function AgbPage() {
  return (
    <main className="min-h-[calc(100vh-3.5rem)] bg-[#0A0E17] px-4 py-12 text-slate-100 sm:px-6 lg:px-8">
      <article className="surface-panel mx-auto max-w-3xl rounded-2xl border border-white/10 bg-[#0F1522] p-6 sm:p-10 space-y-8 text-slate-300">
        <header className="border-b border-white/10 pb-6 space-y-2">
          <p className="text-xs font-semibold text-emerald-400">
            Terms of Service • Nutzungs- und Geschäftsbedingungen
          </p>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            Allgemeine Geschäftsbedingungen (AGB)
          </h1>
          <p className="text-sm text-slate-400 leading-relaxed">
            Transparent service boundaries, user verification responsibilities, and usage rules for FormFlow / AI Form Assistant.
          </p>
        </header>

        <section className="rounded-xl border border-white/[0.08] bg-[#0A0E17] p-4 space-y-1.5 text-xs leading-relaxed text-slate-300">
          <p className="font-semibold text-white">Key Takeaways in Plain English:</p>
          <p>
            FormFlow helps you read, understand, and transcribe answers onto official forms in your language. <strong className="text-slate-100">We are not a law firm, tax advisor, immigration consultant, or government office.</strong> We never submit documents on your behalf, and you must verify every field on your exported PDF before signing or submitting it.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            § 1 Leistungsgegenstand (Scope of Service)
          </h2>
          <p>
            FormFlow / AI Form Assistant stellt eine webbasierte Software zur mehrsprachigen Verständnishilfe, deterministischen Formatprüfung (z. B. Datumsangaben, PLZ, IBAN-Prüfziffern) und technischen Befüllung von PDF-Formularen bereit. Eine automatische Übermittlung von Formularen an Behörden, Versicherungen, Vermieter oder sonstige Dritte findet nicht statt.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            § 2 Ausschluss von Rechts- und Steuerberatung (Rechtsdienstleistungsgesetz — RDG)
          </h2>
          <p>
            Die Plattform erbringt <strong className="text-slate-100">keine Rechtsdienstleistungen im Sinne des § 2 Rechtsdienstleistungsgesetz (RDG)</strong> sowie keine Steuer-, Sozialversicherungs- oder Migrationsberatung. Bereitgestellte Feldhinweise und Checklisten dienen ausschließlich der allgemeinen sprachlichen und organisatorischen Orientierung und ersetzen keine fachkundige Beratung im Einzelfall.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            § 3 Eigenverantwortliche Endkontrolle durch Nutzerinnen und Nutzer
          </h2>
          <p>
            Automatisierte Texterkennung (OCR), Übersetzungen und Feldzuordnungen können insbesondere bei gescannten Dokumenten Abweichungen aufweisen. Nutzerinnen und Nutzer sind verpflichtet, sämtliche eingetragenen Werte im Zwei-Spalten-Prüfstudio sowie im exportierten PDF-Dokument vor der Unterzeichnung und Einreichung vollständig auf Richtigkeit und Vollständigkeit zu kontrollieren.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            § 4 Faire Nutzung, Seitenlimits &amp; Digitale Dokumentenpässe
          </h2>
          <p>
            Zur Sicherstellung stabiler Antwortzeiten gelten technische Schutzgrenzen (maximal 10 MB Dateigröße bzw. 20 Seiten pro Dokument sowie Sitzungs-Kontingente). Kostenlose Sitzungen ermöglichen die geführte Beantwortung und eine mit Wasserzeichen versehene PDF-Vorschau. Bei Einführung kostenpflichtiger Einzel-Dokumentenpässe oder Pakete werden Bruttopreise inklusive gesetzlicher Umsatzsteuer sowie gesetzliche Widerrufshinweise für digitale Inhalte (§ 356 Abs. 5 BGB) vor jedem Kaufabschluss transparent ausgewiesen.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            § 5 Haftung und Anwendbares Recht
          </h2>
          <p>
            Wir haften unbeschränkt bei Vorsatz, grober Fahrlässigkeit sowie bei Verletzung von Leben, Körper oder Gesundheit. Bei leicht fahrlässiger Verletzung wesentlicher Vertragspflichten ist die Haftung auf den vertragstypischen, vorhersehbaren Schaden begrenzt. Es gilt das Recht der Bundesrepublik Deutschland unter Beachtung zwingender Verbraucherschutzvorschriften Ihres gewöhnlichen Aufenthaltsstaates innerhalb der Europäischen Union.
          </p>
        </section>

        <footer className="border-t border-white/10 pt-5 flex flex-wrap gap-4 text-xs font-medium text-emerald-400">
          <Link href="/impressum" className="hover:text-emerald-300 hover:underline transition-colors motion-reduce:transition-none">
            Impressum
          </Link>
          <Link href="/datenschutz" className="hover:text-emerald-300 hover:underline transition-colors motion-reduce:transition-none">
            Datenschutzerklärung (Privacy Policy)
          </Link>
          <Link href="/" className="hover:text-emerald-300 hover:underline transition-colors motion-reduce:transition-none">
            Zur Startseite
          </Link>
        </footer>
      </article>
    </main>
  );
}
