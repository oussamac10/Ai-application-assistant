import React from "react";
import Link from "next/link";

export default function DatenschutzPage() {
  return (
    <main className="min-h-[calc(100vh-3.5rem)] bg-[#0A0E17] px-4 py-12 text-slate-100 sm:px-6 lg:px-8">
      <article className="surface-panel mx-auto max-w-3xl rounded-2xl border border-white/10 bg-[#0F1522] p-6 sm:p-10 space-y-8 text-slate-300">
        <header className="border-b border-white/10 pb-6 space-y-2">
          <p className="text-xs font-semibold text-emerald-400">
            EU General Data Protection Regulation • Art. 13 &amp; 14 DSGVO
          </p>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            Datenschutzerklärung (Privacy Policy)
          </h1>
          <p className="text-sm text-slate-400 leading-relaxed">
            How FormFlow / AI Form Assistant processes, encrypts, and automatically deletes personal form data in compliance with the EU GDPR (DSGVO).
          </p>
        </header>

        <section className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 space-y-2 text-xs leading-relaxed text-emerald-300">
          <p className="font-semibold text-white">Summary in Plain English (International Users):</p>
          <ul className="list-disc ps-5 space-y-1">
            <li><strong className="text-white">Guest sessions auto-expire after 24 hours:</strong> Uploaded PDFs/photos, answers, and exports created without an account are automatically purged.</li>
            <li><strong className="text-white">Encrypted Profile Vault (Optional):</strong> If you create an account and save reusable fields, values are encrypted at rest with symmetric Fernet encryption.</li>
            <li><strong className="text-white">Deterministic validation first:</strong> Dates, emails, postal codes, and IBAN checksums are validated locally by deterministic Python code — never used to train AI models.</li>
            <li><strong className="text-white">1-Click GDPR Rights:</strong> Registered users can download a portable JSON export (Art. 20 DSGVO) or permanently erase their account and files (Art. 17 DSGVO) directly under <Link href="/account" className="text-white underline font-semibold hover:text-emerald-300">/account</Link>.</li>
          </ul>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            1. Verantwortlicher (Controller)
          </h2>
          <p>
            Verantwortlich für die Datenverarbeitung auf dieser Plattform ist der im{" "}
            <Link href="/impressum" className="text-emerald-400 hover:text-emerald-300 underline transition-colors motion-reduce:transition-none">
              Impressum
            </Link>{" "}
            genannte Diensteanbieter (<bdi className="font-mono text-xs text-slate-100">[FOUNDER_LEGAL_NAME]</bdi>, Kontakt: <bdi className="font-mono text-xs text-slate-100">[CONTACT_EMAIL]</bdi>).
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            2. Zwecke und Rechtsgrundlagen der Verarbeitung (Art. 6 Abs. 1 DSGVO)
          </h2>
          <p>
            Wir verarbeiten hochgeladene Formulare, Antworten und Sitzungsmetadaten ausschließlich zur Durchführung der von Ihnen angeforderten mehrsprachigen Ausfüll- und PDF-Exportfunktion (Art. 6 Abs. 1 lit. b DSGVO) sowie zur Missbrauchs- und Sicherheitsabwehr mittels technisch notwendiger HTTP-Only-Sitzungs- und CSRF-Tokens (Art. 6 Abs. 1 lit. f DSGVO). Wir setzen <strong className="text-slate-100">keine Werbe- oder Tracking-Cookies</strong> ein.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            3. Speicherdauer &amp; Automatische 24-Stunden-Löschung
          </h2>
          <ul className="list-disc ps-5 space-y-1.5">
            <li>
              <strong className="text-slate-100">Gast-Sitzungen (ohne Konto):</strong> Hochgeladene Dokumente, Sitzungsantworten und generierte PDF-Exporte werden nach Ablauf von <strong className="text-slate-100">24 Stunden</strong> automatisch und unwiderruflich durch unseren Hintergrund-Bereinigungsdienst gelöscht.
            </li>
            <li>
              <strong className="text-slate-100">Registrierte Konten &amp; Profil-Tresor:</strong> Gespeicherte Anträge und im verschlüsselten Profil-Tresor hinterlegte Standardangaben bleiben bis zu Ihrer aktiven Löschung gespeichert.
            </li>
            <li>
              <strong className="text-slate-100">Zero-PII-Protokollierung:</strong> Server- und Audit-Protokolle speichern ausschließlich technische Korrelations-IDs, Zeitstempel und Fehlercodes — niemals Klartext-Antworten, IBANs, Unterschriften oder Dokumentinhalte.
            </li>
          </ul>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            4. Einsatz von EU-Cloud-, OCR- und KI-Diensten (Auftragsverarbeitung)
          </h2>
          <p>
            Für vorab geprüfte deutsche Standardformulare erfolgt die Felderkennung und Fragenzuordnung vollständig lokal ohne externe Dokumentenanalyse. Bei unbekannten Nutzer-Uploads werden zur Layout-/Texterkennung und sprachlichen Erklärung Auftragsverarbeiter mit EU-Datenverarbeitung (insb. EU-Hosting, Microsoft Azure EU-Regionen für OCR/Übersetzung sofern aktiviert, sowie Google Cloud / Gemini API über verschlüsselte HTTPS-Verbindungen ohne Trainingsfreigabe für bezahlte API-Aufrufe) eingesetzt.
          </p>
        </section>

        <section className="space-y-2 text-sm leading-relaxed">
          <h2 className="text-base font-bold text-white">
            5. Ihre Rechte (Art. 15–21 DSGVO — Selbstbedienung im Konto)
          </h2>
          <p>
            Sie haben jederzeit das Recht auf Auskunft (Art. 15 DSGVO), Berichtigung (Art. 16 DSGVO), <strong className="text-slate-100">unverzügliche Löschung / Recht auf Vergessenwerden (Art. 17 DSGVO)</strong>, Einschränkung der Verarbeitung (Art. 18 DSGVO) sowie <strong className="text-slate-100">Datenübertragbarkeit im maschinenlesbaren JSON-Format (Art. 20 DSGVO)</strong>. Registrierte Nutzerinnen und Nutzer können den vollständigen JSON-Datenexport und die sofortige Kontolöschung jederzeit selbstständig unter{" "}
            <Link href="/account" className="text-emerald-400 hover:text-emerald-300 underline transition-colors motion-reduce:transition-none">
              Konto &amp; Datenschutz (/account)
            </Link>{" "}
            ausführen. Zudem besteht ein Beschwerderecht bei einer Datenschutz-Aufsichtsbehörde (Art. 77 DSGVO).
          </p>
        </section>

        <footer className="border-t border-white/10 pt-5 flex flex-wrap gap-4 text-xs font-medium text-emerald-400">
          <Link href="/impressum" className="hover:text-emerald-300 hover:underline transition-colors motion-reduce:transition-none">
            Impressum
          </Link>
          <Link href="/agb" className="hover:text-emerald-300 hover:underline transition-colors motion-reduce:transition-none">
            AGB (Terms of Service)
          </Link>
          <Link href="/account" className="hover:text-emerald-300 hover:underline transition-colors motion-reduce:transition-none">
            DSGVO-Selbstbedienung (/account)
          </Link>
        </footer>
      </article>
    </main>
  );
}
