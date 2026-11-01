import React from "react";
import Link from "next/link";

export default function DatenschutzPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <article className="surface-panel rounded-2xl p-6 sm:p-10 space-y-8 text-slate-800">
        <header className="border-b border-slate-200 pb-6 space-y-2">
          <p className="text-xs font-semibold text-indigo-700">
            EU General Data Protection Regulation • Art. 13 &amp; 14 DSGVO
          </p>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
            Datenschutzerklärung (Privacy Policy)
          </h1>
          <p className="text-sm text-slate-600 leading-relaxed">
            How FormFlow / AI Form Assistant processes, encrypts, and automatically deletes personal form data in compliance with the EU GDPR (DSGVO).
          </p>
        </header>

        <section className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4 space-y-2 text-xs leading-relaxed text-emerald-950">
          <p className="font-semibold">Summary in Plain English (International Users):</p>
          <ul className="list-disc ps-5 space-y-1">
            <li><strong>Guest sessions auto-expire after 24 hours:</strong> Uploaded PDFs/photos, answers, and exports created without an account are automatically purged.</li>
            <li><strong>Encrypted Profile Vault (Optional):</strong> If you create an account and save reusable fields, values are encrypted at rest with symmetric Fernet encryption.</li>
            <li><strong>Deterministic validation first:</strong> Dates, emails, postal codes, and IBAN checksums are validated locally by deterministic Python code — never used to train AI models.</li>
            <li><strong>1-Click GDPR Rights:</strong> Registered users can download a portable JSON export (Art. 20 DSGVO) or permanently erase their account and files (Art. 17 DSGVO) directly under <Link href="/account" className="underline font-semibold">/account</Link>.</li>
          </ul>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            1. Verantwortlicher (Controller)
          </h2>
          <p>
            Verantwortlich für die Datenverarbeitung auf dieser Plattform ist der im{" "}
            <Link href="/impressum" className="text-indigo-700 underline">
              Impressum
            </Link>{" "}
            genannte Diensteanbieter (<bdi className="font-mono text-xs">[FOUNDER_LEGAL_NAME]</bdi>, Kontakt: <bdi className="font-mono text-xs">[CONTACT_EMAIL]</bdi>).
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            2. Zwecke und Rechtsgrundlagen der Verarbeitung (Art. 6 Abs. 1 DSGVO)
          </h2>
          <p>
            Wir verarbeiten hochgeladene Formulare, Antworten und Sitzungsmetadaten ausschließlich zur Durchführung der von Ihnen angeforderten mehrsprachigen Ausfüll- und PDF-Exportfunktion (Art. 6 Abs. 1 lit. b DSGVO) sowie zur Missbrauchs- und Sicherheitsabwehr mittels technisch notwendiger HTTP-Only-Sitzungs- und CSRF-Tokens (Art. 6 Abs. 1 lit. f DSGVO). Wir setzen <strong>keine Werbe- oder Tracking-Cookies</strong> ein.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            3. Speicherdauer &amp; Automatische 24-Stunden-Löschung
          </h2>
          <ul className="list-disc ps-5 space-y-1.5">
            <li>
              <strong>Gast-Sitzungen (ohne Konto):</strong> Hochgeladene Dokumente, Sitzungsantworten und generierte PDF-Exporte werden nach Ablauf von <strong>24 Stunden</strong> automatisch und unwiderruflich durch unseren Hintergrund-Bereinigungsdienst gelöscht.
            </li>
            <li>
              <strong>Registrierte Konten &amp; Profil-Tresor:</strong> Gespeicherte Anträge und im verschlüsselten Profil-Tresor hinterlegte Standardangaben bleiben bis zu Ihrer aktiven Löschung gespeichert.
            </li>
            <li>
              <strong>Zero-PII-Protokollierung:</strong> Server- und Audit-Protokolle speichern ausschließlich technische Korrelations-IDs, Zeitstempel und Fehlercodes — niemals Klartext-Antworten, IBANs, Unterschriften oder Dokumentinhalte.
            </li>
          </ul>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            4. Einsatz von EU-Cloud-, OCR- und KI-Diensten (Auftragsverarbeitung)
          </h2>
          <p>
            Für vorab geprüfte deutsche Standardformulare erfolgt die Felderkennung und Fragenzuordnung vollständig lokal ohne externe Dokumentenanalyse. Bei unbekannten Nutzer-Uploads werden zur Layout-/Texterkennung und sprachlichen Erklärung Auftragsverarbeiter mit EU-Datenverarbeitung (insb. EU-Hosting, Microsoft Azure EU-Regionen für OCR/Übersetzung sofern aktiviert, sowie Google Cloud / Gemini API über verschlüsselte HTTPS-Verbindungen ohne Trainingsfreigabe für bezahlte API-Aufrufe) eingesetzt.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-slate-900">
            5. Ihre Rechte (Art. 15–21 DSGVO — Selbstbedienung im Konto)
          </h2>
          <p>
            Sie haben jederzeit das Recht auf Auskunft (Art. 15 DSGVO), Berichtigung (Art. 16 DSGVO), <strong>unverzügliche Löschung / Recht auf Vergessenwerden (Art. 17 DSGVO)</strong>, Einschränkung der Verarbeitung (Art. 18 DSGVO) sowie <strong>Datenübertragbarkeit im maschinenlesbaren JSON-Format (Art. 20 DSGVO)</strong>. Registrierte Nutzerinnen und Nutzer können den vollständigen JSON-Datenexport und die sofortige Kontolöschung jederzeit selbstständig unter{" "}
            <Link href="/account" className="text-indigo-700 underline">
              Konto &amp; Datenschutz (/account)
            </Link>{" "}
            ausführen. Zudem besteht ein Beschwerderecht bei einer Datenschutz-Aufsichtsbehörde (Art. 77 DSGVO).
          </p>
        </section>

        <footer className="border-t border-slate-200 pt-5 flex flex-wrap gap-4 text-xs font-medium text-indigo-700">
          <Link href="/impressum" className="hover:underline">
            Impressum
          </Link>
          <Link href="/agb" className="hover:underline">
            AGB (Terms of Service)
          </Link>
          <Link href="/account" className="hover:underline">
            DSGVO-Selbstbedienung (/account)
          </Link>
        </footer>
      </article>
    </main>
  );
}
