"""Plain-language field explanations and post-completion submission checklists.

Product boundary invariant (per `.agents/AGENTS.md` Section 4 & 6.1):
- Explanations clarify bureaucratic terminology in simple, everyday words and
  tell the user where to find the requested information on official letters or
  documents.
- Never provide legal advice, financial advice, or eligibility conclusions.
- Prefer deterministic, reviewed multilingual catalogs (`en`, `de`, `fr`, `ar`)
  so common fields never trigger unnecessary AI calls.
"""

from __future__ import annotations

from typing import Any

from app.answers.signatures import PENDING_MANUAL_SIGNATURE
from app.forms.models import FormField, FormVersion

_SUPPORTED_LANGS = ("en", "de", "fr", "ar")


def _pick_lang(user_language: str) -> str:
    lang = (user_language or "en").strip().lower().split("-")[0]
    return lang if lang in _SUPPORTED_LANGS else "en"


_EXPLANATION_CATALOG: tuple[tuple[tuple[str, ...], dict[str, dict[str, str]]], ...] = (
    (
        ("iban",),
        {
            "en": {
                "summary": "Your International Bank Account Number (IBAN) used for bank transfers or rent payments.",
                "where_to_find": "Printed on the front or back of your debit/bank card, on your bank statement (Kontoauszug), or in your banking app under Account Details.",
                "example": "DE89 3704 0044 0532 0130 00",
            },
            "de": {
                "summary": "Ihre internationale Bankkontonummer (IBAN) für Überweisungen oder Mietzahlungen.",
                "where_to_find": "Auf Ihrer Girocard/Bankkarte, auf dem Kontoauszug oder in Ihrer Banking-App unter Kontodetails.",
                "example": "DE89 3704 0044 0532 0130 00",
            },
            "fr": {
                "summary": "Votre numéro de compte bancaire international (IBAN) utilisé pour les virements ou le paiement du loyer.",
                "where_to_find": "Sur votre relevé d'identité bancaire (RIB), votre relevé de compte ou dans votre application bancaire.",
                "example": "FR76 3000 6000 0112 3456 7890 189",
            },
            "ar": {
                "summary": "رقم الحساب البنكي الدولي (IBAN) المستخدم للتحويلات البنكية أو دفع الإيجار.",
                "where_to_find": "مطبوع على بطاقتك البنكية، أو في كشف الحساب البنكي، أو داخل تطبيق البنك في تفاصيل الحساب.",
                "example": "DE89 3704 0044 0532 0130 00",
            },
        },
    ),
    (
        ("bic", "swift"),
        {
            "en": {
                "summary": "The Bank Identifier Code (BIC/SWIFT) that identifies the specific bank alongside the IBAN.",
                "where_to_find": "Listed right next to the IBAN on your bank statement (Kontoauszug / RIB) or in your online banking portal.",
                "example": "COBADEFFXXX",
            },
            "de": {
                "summary": "Die internationale Bankleitzahl (BIC/SWIFT), die das Kreditinstitut eindeutig identifiziert.",
                "where_to_find": "Direkt neben der IBAN auf Ihrem Kontoauszug oder im Online-Banking unter Kontoinformationen.",
                "example": "COBADEFFXXX",
            },
            "fr": {
                "summary": "Le code d'identification bancaire (BIC/SWIFT) qui identifie la banque avec l'IBAN.",
                "where_to_find": "Indiqué à côté de l'IBAN sur votre RIB ou sur votre relevé bancaire.",
                "example": "BNPAFRPPXXX",
            },
            "ar": {
                "summary": "رمز تعريف البنك (BIC/SWIFT) الذي يحدد اسم البنك بجانب رقم IBAN.",
                "where_to_find": "موجود بجانب رقم IBAN في كشف الحساب البنكي أو في تطبيق البنك.",
                "example": "COBADEFFXXX",
            },
        },
    ),
    (
        ("kontoinhaber", "account_holder", "titulaire"),
        {
            "en": {
                "summary": "The full name of the person or organization that owns the bank account.",
                "where_to_find": "Printed on the bank card or listed in the payment section of the rental contract.",
                "example": "Max Mustermann",
            },
            "de": {
                "summary": "Der vollständige Name der Person oder Organisation, auf die das Bankkonto läuft.",
                "where_to_find": "Auf der Bankkarte oder im Mietvertrag unter den Zahlungsangaben des Vermieters.",
                "example": "Max Mustermann",
            },
            "fr": {
                "summary": "Le nom complet de la personne ou de l'organisme titulaire du compte bancaire.",
                "where_to_find": "Sur votre RIB ou dans la section paiement du contrat.",
                "example": "Jean Dupont",
            },
            "ar": {
                "summary": "الاسم الكامل لصاحب الحساب البنكي (شخص أو جهة).",
                "where_to_find": "مكتوب على البطاقة البنكية أو في قسم الدفع داخل عقد الإيجار.",
                "example": "Max Mustermann",
            },
        },
    ),
    (
        ("grundmiete", "kaltmiete"),
        {
            "en": {
                "summary": "The monthly base rent (Kaltmiete) for the apartment alone, before utility and heating advances.",
                "where_to_find": "In the rent section (§ Mietkosten / Miete) of your rental contract (Mietvertrag).",
                "example": "850 EUR",
            },
            "de": {
                "summary": "Die monatliche Nettokaltmiete für die Wohnung ohne Betriebskosten und Heizkosten.",
                "where_to_find": "Im Mietvertrag im Abschnitt „§ Mietkosten“ bzw. „Miete“.",
                "example": "850 EUR",
            },
            "fr": {
                "summary": "Le loyer mensuel hors charges (Grundmiete / Kaltmiete) avant les provisions pour charges et chauffage.",
                "where_to_find": "Dans la section loyer (§ Mietkosten) de votre contrat de bail.",
                "example": "850 EUR",
            },
            "ar": {
                "summary": "قيمة الإيجار الأساسي الشهري للشقة (بدون تكاليف الخدمات والتدفئة).",
                "where_to_find": "في قسم تكاليف الإيجار (§ Mietkosten) داخل عقد الإيجار.",
                "example": "850 EUR",
            },
        },
    ),
    (
        ("betriebskosten", "nebenkosten"),
        {
            "en": {
                "summary": "Monthly advance payment for building operating costs (water, waste collection, cleaning, property tax).",
                "where_to_find": "Listed under 'Betriebskostenvorauszahlung' or 'Nebenkosten' in the rent section of your rental contract.",
                "example": "150 EUR",
            },
            "de": {
                "summary": "Monatliche Vorauszahlung für die allgemeinen Betriebskosten des Hauses (z. B. Wasser, Müllabfuhr, Hausreinigung).",
                "where_to_find": "Im Mietvertrag unter „Betriebskostenvorauszahlung“ oder „Nebenkosten“.",
                "example": "150 EUR",
            },
            "fr": {
                "summary": "Provision mensuelle pour les charges locatives d'exploitation (eau, ordures ménagères, entretien).",
                "where_to_find": "Indiquée sous « Betriebskostenvorauszahlung » dans votre contrat de location.",
                "example": "150 EUR",
            },
            "ar": {
                "summary": "دفعة شهرية مقدمة لتكاليف تشغيل المبنى (المياه، جمع النفايات، صيانة المبنى).",
                "where_to_find": "مذكورة تحت بند Betriebskostenvorauszahlung في عقد الإيجار.",
                "example": "150 EUR",
            },
        },
    ),
    (
        ("heizkosten",),
        {
            "en": {
                "summary": "Monthly advance payment for heating and hot water (Heizkostenvorauszahlung).",
                "where_to_find": "Listed right below the base rent and operating costs in your rental contract.",
                "example": "110 EUR",
            },
            "de": {
                "summary": "Monatliche Vorauszahlung für Heizung und Warmwasser (Heizkostenvorauszahlung).",
                "where_to_find": "Im Mietvertrag im Abschnitt „Mietkosten“ direkt unter den Betriebskosten.",
                "example": "110 EUR",
            },
            "fr": {
                "summary": "Provision mensuelle pour le chauffage et l'eau chaude (Heizkostenvorauszahlung).",
                "where_to_find": "Indiquée dans la section des coûts de location de votre bail.",
                "example": "110 EUR",
            },
            "ar": {
                "summary": "دفعة شهرية مقدمة لتكاليف التدفئة والمياه الساخنة.",
                "where_to_find": "مدرجة تحت بند Heizkostenvorauszahlung في عقد الإيجار.",
                "example": "110 EUR",
            },
        },
    ),
    (
        ("kaution", "mietsicherheit"),
        {
            "en": {
                "summary": "The refundable rental security deposit agreed between tenant and landlord.",
                "where_to_find": "Listed in your rental contract under 'Kaution' or 'Mietsicherheit'.",
                "example": "2,000 EUR",
            },
            "de": {
                "summary": "Die vereinbarte Mietsicherheit (Kaution), die zu Beginn des Mietverhältnisses hinterlegt wird.",
                "where_to_find": "Im Mietvertrag oder Übergabeprotokoll unter „Kaution“ bzw. „Mietsicherheit“.",
                "example": "2.000 EUR",
            },
            "fr": {
                "summary": "Le dépôt de garantie remboursable prévu au début de la location.",
                "where_to_find": "Dans votre contrat de location sous la rubrique « Kaution » ou « Dépôt de garantie ».",
                "example": "2 000 EUR",
            },
            "ar": {
                "summary": "مبلغ التأمين القابل للاسترداد (Kaution) المتفق عليه عند بداية الإيجار.",
                "where_to_find": "مذكور في عقد الإيجار تحت بند Kaution أو Mietsicherheit.",
                "example": "2,000 EUR",
            },
        },
    ),
    (
        ("txtortdatum1_ort", "txtortdatum2_ort", "_ort"),
        {
            "en": {
                "summary": "The city (Ort) where this form is being signed.",
                "where_to_find": "Enter the city where the person signing is located at the time of signature.",
                "example": "Stuttgart",
            },
            "de": {
                "summary": "Der Ort, an dem das Formular unterschrieben wird.",
                "where_to_find": "Tragen Sie die Stadt ein, in der die Unterschrift geleistet wird.",
                "example": "Stuttgart",
            },
            "fr": {
                "summary": "La ville (Ort) où ce formulaire est signé.",
                "where_to_find": "Indiquez la ville où se trouve le signataire au moment de la signature.",
                "example": "Stuttgart",
            },
            "ar": {
                "summary": "المدينة (Ort) التي يتم فيها توقيع هذه الاستمارة.",
                "where_to_find": "اكتب اسم المدينة التي يتم فيها التوقيع.",
                "example": "Stuttgart",
            },
        },
    ),
    (
        ("einzug", "auszug", "move_in", "move_out", "mietbeginn"),
        {
            "en": {
                "summary": "The official move-in or move-out date when you actually move into or leave the apartment.",
                "where_to_find": "Check your rental contract (Mietvertrag) or apartment handover protocol (Übergabeprotokoll) for the exact move-in date.",
                "example": "01.11.2026",
            },
            "de": {
                "summary": "Das tatsächliche Einzugs- bzw. Auszugsdatum, an dem Sie die Wohnung beziehen oder verlassen.",
                "where_to_find": "Prüfen Sie Ihren Mietvertrag oder das Wohnungsübergabeprotokoll für das genaue Datum.",
                "example": "01.11.2026",
            },
            "fr": {
                "summary": "La date réelle d'emménagement ou de déménagement dans le logement.",
                "where_to_find": "Vérifiez votre contrat de bail ou l'état des lieux d'entrée.",
                "example": "01.11.2026",
            },
            "ar": {
                "summary": "تاريخ الانتقال الفعلي للسكن (Einzug) أو مغادرته (Auszug).",
                "where_to_find": "راجع عقد الإيجار أو محضر استلام الشقة للتأكد من تاريخ الانتقال الدقيق.",
                "example": "01.11.2026",
            },
        },
    ),
    (
        (
            "txtortdatum1_datum",
            "txtortdatum2_datum",
            "ortdatum_datum",
            "unterschrift_datum",
        ),
        {
            "en": {
                "summary": "The date (Datum) on which this form is signed.",
                "where_to_find": "Enter the date of signature (typically today's date).",
                "example": "25.10.2026",
            },
            "de": {
                "summary": "Das Datum, an dem das Formular unterschrieben wird.",
                "where_to_find": "Tragen Sie das Unterschriftsdatum (in der Regel das heutige Datum) ein.",
                "example": "25.10.2026",
            },
            "fr": {
                "summary": "La date (Datum) à laquelle ce formulaire est signé.",
                "where_to_find": "Indiquez la date de signature (généralement la date du jour).",
                "example": "25.10.2026",
            },
            "ar": {
                "summary": "تاريخ (Datum) توقيع هذه الاستمارة.",
                "where_to_find": "أدخل تاريخ التوقيع (عادةً تاريخ اليوم).",
                "example": "25.10.2026",
            },
        },
    ),
    (
        ("ort_datum", "txtortdatum"),
        {
            "en": {
                "summary": "The city where the form is signed and the date of signing.",
                "where_to_find": "Enter your current city followed by today's date.",
                "example": "Stuttgart, 25.10.2026",
            },
            "de": {
                "summary": "Der Ort, an dem das Formular unterschrieben wird, sowie das aktuelle Datum.",
                "where_to_find": "Tragen Sie Ihren aktuellen Ort und das heutige Datum ein.",
                "example": "Stuttgart, 25.10.2026",
            },
            "fr": {
                "summary": "La ville où le formulaire est signé ainsi que la date de signature.",
                "where_to_find": "Indiquez votre ville actuelle suivie de la date du jour.",
                "example": "Stuttgart, 25.10.2026",
            },
            "ar": {
                "summary": "المدينة التي يتم فيها توقيع الاستمارة وتاريخ التوقيع.",
                "where_to_find": "اكتب اسم مدينتك الحالية متبوعاً بتاريخ اليوم.",
                "example": "Stuttgart, 25.10.2026",
            },
        },
    ),
    (
        ("wohnungsgeber", "vermieter", "eigentümer", "eigentumer"),
        {
            "en": {
                "summary": "Details of the housing provider / landlord (Wohnungsgeber / Vermieter) or property owner (Eigentümer) who grants you use of the apartment.",
                "where_to_find": "On page 1 of your rental contract (Mietvertrag) under 'Vermieter' or in your landlord's contact letter.",
                "example": "Anna Beispiel, Hauptstraße 10, 70173 Stuttgart",
            },
            "de": {
                "summary": "Angaben zum Wohnungsgeber / Vermieter bzw. Wohnungseigentümer, der Ihnen die Wohnung überlässt.",
                "where_to_find": "Auf der ersten Seite Ihres Mietvertrags unter „Vermieter“.",
                "example": "Anna Beispiel, Hauptstraße 10, 70173 Stuttgart",
            },
            "fr": {
                "summary": "Coordonnées du bailleur / logeur (Wohnungsgeber / Vermieter) ou du propriétaire du logement.",
                "where_to_find": "Sur la première page de votre contrat de location sous la rubrique « Vermieter ».",
                "example": "Anna Beispiel, Hauptstraße 10, 70173 Stuttgart",
            },
            "ar": {
                "summary": "بيانات المؤجر أو مقدم السكن (Wohnungsgeber / Vermieter) أو مالك العقار.",
                "where_to_find": "في الصفحة الأولى من عقد الإيجار تحت بند Vermieter.",
                "example": "Anna Beispiel, Hauptstraße 10, 70173 Stuttgart",
            },
        },
    ),
    (
        ("anschrift", "straße", "strasse", "plz", "postleitzahl", "adresse", "im_haus"),
        {
            "en": {
                "summary": "The full street address including street name, house number, postal code (PLZ), and city (Ort).",
                "where_to_find": "On your rental contract (Mietvertrag), registration certificate (Meldebescheinigung), or official letters.",
                "example": "Landhausstraße 260, 70188 Stuttgart",
            },
            "de": {
                "summary": "Die vollständige Anschrift mit Straßenname, Hausnummer, Postleitzahl (PLZ) und Ort.",
                "where_to_find": "In Ihrem Mietvertrag, auf der Meldebescheinigung oder in offiziellen Schreiben.",
                "example": "Landhausstraße 260, 70188 Stuttgart",
            },
            "fr": {
                "summary": "L'adresse complète comprenant la rue, le numéro, le code postal (PLZ) et la ville (Ort).",
                "where_to_find": "Sur votre contrat de bail, votre attestation d'enregistrement ou un justificatif de domicile.",
                "example": "12 Rue de Rivoli, 75001 Paris",
            },
            "ar": {
                "summary": "العنوان الكامل ويشمل اسم الشارع، رقم المبنى، الرمز البريدي (PLZ)، والمدينة (Ort).",
                "where_to_find": "في عقد الإيجار أو شهادة التسجيل السكني (Meldebescheinigung).",
                "example": "Landhausstraße 260, 70188 Stuttgart",
            },
        },
    ),
    (
        ("geburtsdatum", "birth_date", "date_of_birth", "naissance"),
        {
            "en": {
                "summary": "Your official date of birth (day, month, and four-digit year).",
                "where_to_find": "Exactly as printed on your passport, national ID card, or birth certificate.",
                "example": "15.09.2000",
            },
            "de": {
                "summary": "Ihr offizielles Geburtsdatum (Tag, Monat und vierstellige Jahreszahl).",
                "where_to_find": "Genau wie in Ihrem Reisepass, Personalausweis oder Ihrer Geburtsurkunde angegeben.",
                "example": "15.09.2000",
            },
            "fr": {
                "summary": "Votre date de naissance officielle (jour, mois et année à quatre chiffres).",
                "where_to_find": "Exactement comme indiqué sur votre passeport ou pièce d'identité.",
                "example": "15.09.2000",
            },
            "ar": {
                "summary": "تاريخ ميلادك الرسمي (اليوم، الشهر، والسنة من أربعة أرقام).",
                "where_to_find": "كما هو مدون في جواز السفر أو بطاقة الهوية الوطنية.",
                "example": "15.09.2000",
            },
        },
    ),
)

_FALLBACK_BY_TYPE: dict[str, dict[str, dict[str, str]]] = {
    "signature": {
        "en": {
            "summary": "Official signature confirming the information on this document. You can draw your signature digitally here or choose 'Sign after printing' to sign on paper.",
            "where_to_find": "If the label asks for the landlord's or housing provider's signature, select 'Sign after printing' so they can sign the printed PDF.",
            "example": "Draw on pad or choose 'Sign after printing'",
        },
        "de": {
            "summary": "Offizielle Unterschrift zur Bestätigung der Angaben. Sie können hier digital unterschreiben oder „Nach dem Ausdrucken unterschreiben“ wählen.",
            "where_to_find": "Falls die Unterschrift des Vermieters/Wohnungsgebers gefragt ist, wählen Sie „Nach dem Ausdrucken unterschreiben“, damit diese Person auf Papier unterschreiben kann.",
            "example": "Digital zeichnen oder auf dem Ausdruck unterschreiben",
        },
        "fr": {
            "summary": "Signature officielle confirmant les informations du formulaire. Vous pouvez signer numériquement ici ou choisir « Signer après impression ».",
            "where_to_find": "Si la signature du bailleur est demandée, choisissez « Signer après impression » pour faire signer le document imprimé.",
            "example": "Signature dessinée ou signature sur papier après impression",
        },
        "ar": {
            "summary": "التوقيع الرسمي لتأكيد البيانات الواردة في الاستمارة. يمكنك رسم توقيعك رقمياً هنا أو اختيار «التوقيع بعد الطباعة» للتوقيع يدوياً على الورق.",
            "where_to_find": "إذا كان الحقل يطلب توقيع المؤجر، اختر «التوقيع بعد الطباعة» ليقوم بتوقيع النسخة المطبوعة.",
            "example": "توقيع رقمي أو يدوي بعد الطباعة",
        },
    },
    "date": {
        "en": {
            "summary": "A calendar date required by the form (for example start date, move-in date, or birth date).",
            "where_to_find": "Check your rental contract, official notice, or identity document for the exact date.",
            "example": "01.11.2026",
        },
        "de": {
            "summary": "Ein vom Formular gefordertes Kalenderdatum (z. B. Vertragsbeginn, Einzugsdatum oder Geburtsdatum).",
            "where_to_find": "Prüfen Sie Ihren Mietvertrag, den offiziellen Bescheid oder Ihren Ausweis für das genaue Datum.",
            "example": "01.11.2026",
        },
        "fr": {
            "summary": "Une date civile demandée par le formulaire (par ex. date d'entrée, début de contrat ou date de naissance).",
            "where_to_find": "Vérifiez votre contrat de location, courrier officiel ou pièce d'identité.",
            "example": "01.11.2026",
        },
        "ar": {
            "summary": "تاريخ تقويمي مطلوب في الاستمارة (مثل تاريخ بداية العقد أو تاريخ الانتقال للسكن).",
            "where_to_find": "راجع عقد الإيجار أو الخطاب الرسمي للتأكد من التاريخ الدقيق.",
            "example": "01.11.2026",
        },
    },
    "money": {
        "en": {
            "summary": "A monetary amount together with its currency (such as EUR).",
            "where_to_find": "Listed in your contract, salary slip (Gehaltsabrechnung), or bank statement.",
            "example": "1,200 EUR",
        },
        "de": {
            "summary": "Ein Geldbetrag mit Währungsangabe (z. B. in Euro).",
            "where_to_find": "In Ihrem Vertrag, Ihrer Gehaltsabrechnung oder auf Ihrem Kontoauszug.",
            "example": "1.200 EUR",
        },
        "fr": {
            "summary": "Un montant financier avec sa devise (par exemple EUR).",
            "where_to_find": "Indiqué dans votre contrat, bulletin de salaire ou relevé bancaire.",
            "example": "1 200 EUR",
        },
        "ar": {
            "summary": "مبلغ مالي مع تحديد العملة (مثل اليورو EUR).",
            "where_to_find": "موجود في العقد أو كشف الراتب أو كشف الحساب البنكي.",
            "example": "1,200 EUR",
        },
    },
    "email": {
        "en": {
            "summary": "An active email address where the authority or organization can reach you.",
            "where_to_find": "Use your personal email address that you check regularly.",
            "example": "name@example.com",
        },
        "de": {
            "summary": "Eine aktive E-Mail-Adresse für Rückfragen oder Bestätigungen.",
            "where_to_find": "Verwenden Sie Ihre persönliche E-Mail-Adresse, die Sie regelmäßig abrufen.",
            "example": "name@example.com",
        },
        "fr": {
            "summary": "Une adresse e-mail active où l'administration peut vous contacter.",
            "where_to_find": "Utilisez votre adresse e-mail personnelle consultée régulièrement.",
            "example": "nom@example.com",
        },
        "ar": {
            "summary": "عنوان بريد إلكتروني نشط للتواصل أو إرسال التأكيدات.",
            "where_to_find": "استخدم بريدك الإلكتروني الشخصي الذي تتابعه بانتظام.",
            "example": "name@example.com",
        },
    },
    "phone": {
        "en": {
            "summary": "A telephone or mobile number including country or area code.",
            "where_to_find": "Your active mobile or landline phone number.",
            "example": "+49 170 1234567",
        },
        "de": {
            "summary": "Eine Telefon- oder Mobilfunknummer inklusive Vorwahl.",
            "where_to_find": "Ihre aktuelle Mobilfunk- oder Festnetznummer.",
            "example": "+49 170 1234567",
        },
        "fr": {
            "summary": "Un numéro de téléphone fixe ou mobile avec indicatif.",
            "where_to_find": "Votre numéro de téléphone personnel actif.",
            "example": "+33 6 12 34 56 78",
        },
        "ar": {
            "summary": "رقم الهاتف المحمول أو الثابت مع رمز الدولة أو المدينة.",
            "where_to_find": "رقم هاتفك الشخصي المتاح للتواصل.",
            "example": "+49 170 1234567",
        },
    },
}

_DEFAULT_EXPLANATION: dict[str, dict[str, str]] = {
    "en": {
        "summary": "Enter the exact information requested by this section of the official form.",
        "where_to_find": "Check your passport/ID card, rental contract, or official correspondence for the exact spelling or value.",
        "example": "Write clearly as shown on your official documents",
    },
    "de": {
        "summary": "Tragen Sie die in diesem Abschnitt des offiziellen Formulars geforderten Angaben ein.",
        "where_to_find": "Prüfen Sie Ihren Ausweis/Reisepass, Mietvertrag oder offizielle Unterlagen für die genaue Schreibweise.",
        "example": "Angabe wie auf Ihren offiziellen Dokumenten",
    },
    "fr": {
        "summary": "Saisissez l'information exacte demandée dans cette rubrique du formulaire officiel.",
        "where_to_find": "Vérifiez votre pièce d'identité, contrat de bail ou courrier officiel pour l'orthographe exacte.",
        "example": "Indiquez la valeur figurant sur vos justificatifs",
    },
    "ar": {
        "summary": "أدخل المعلومة المطلوبة في هذا القسم من الاستمارة الرسمية بدقة.",
        "where_to_find": "راجع جواز السفر أو بطاقة الهوية أو عقد الإيجار للتأكد من التهجئة الصحيحة.",
        "example": "كما هو مكتوب في مستنداتك الرسمية",
    },
}


def resolve_field_explanation(
    field: FormField,
    translated_label: str,
    user_language: str,
) -> dict[str, str]:
    """Returns a deterministic plain-language explanation dict (`summary`,
    `where_to_find`, `example`) for `field` in `user_language`.
    """
    lang = _pick_lang(user_language)
    source_labels = " ".join(t.label for t in (field.translations or []) if t.label)
    haystack = " ".join(
        filter(
            None,
            [
                field.key,
                field.question_key,
                translated_label,
                source_labels,
            ],
        )
    ).lower()

    # Signature field type takes precedence so signature boxes always explain
    # digital vs. print-and-sign options clearly.
    if field.field_type == "signature":
        return dict(_FALLBACK_BY_TYPE["signature"][lang])

    for keywords, by_lang in _EXPLANATION_CATALOG:
        if any(kw in haystack for kw in keywords):
            return dict(by_lang[lang])

    if field.field_type in _FALLBACK_BY_TYPE:
        return dict(_FALLBACK_BY_TYPE[field.field_type][lang])

    return dict(_DEFAULT_EXPLANATION[lang])


def build_submission_checklist(
    version: FormVersion,
    answers_by_field_id: dict[str, Any],
    user_language: str,
) -> list[dict[str, Any]]:
    """Generates a deterministic post-completion Submission & Supporting
    Document Checklist tailored to the fields in `version` and `answers_by_field_id`.
    """
    lang = _pick_lang(user_language)
    all_keys_and_labels = " ".join(
        f"{f.key} " + " ".join(t.label for t in (f.translations or []) if t.label)
        for f in (version.fields or [])
    ).lower()

    has_deferred_sig = any(
        getattr(ans, "status", None) == PENDING_MANUAL_SIGNATURE
        for ans in answers_by_field_id.values()
    )
    has_any_sig = any(f.field_type == "signature" for f in (version.fields or []))
    has_landlord_party = any(
        kw in all_keys_and_labels
        for kw in ("wohnungsgeber", "vermieter", "eigentümer", "eigentumer", "bailleur")
    )
    has_bank_fields = any(
        kw in all_keys_and_labels for kw in ("iban", "bic", "kontoinhaber")
    )

    items: list[dict[str, Any]] = []

    # 1. Always include final user review responsibility (AGENTS.md Section 4)
    review_copy = {
        "en": (
            "Review all filled entries on the downloaded PDF",
            "Verify that names, dates, and addresses match your official documents before submitting to the authority.",
        ),
        "de": (
            "Alle eingetragenen Angaben im heruntergeladenen PDF prüfen",
            "Kontrollieren Sie vor der Abgabe, dass Namen, Daten und Anschriften exakt mit Ihren Ausweisdokumenten übereinstimmen.",
        ),
        "fr": (
            "Vérifier toutes les informations dans le PDF téléchargé",
            "Assurez-vous que les noms, dates et adresses correspondent exactement à vos justificatifs officiels avant l'envoi.",
        ),
        "ar": (
            "مراجعة جميع البيانات المدخلة في ملف PDF بعد تحميله",
            "تأكد من مطابقة الأسماء والتواريخ والعناوين لوثائقك الرسمية قبل تقديم الاستمارة للجهة المختصة.",
        ),
    }[lang]
    items.append(
        {
            "id": "review_printed_values",
            "title": review_copy[0],
            "description": review_copy[1],
            "category": "verification",
            "required": True,
        }
    )

    # 2. Handwritten signature reminder when deferred or signature fields exist
    if has_deferred_sig or has_any_sig:
        sig_copy = {
            "en": (
                "Print and sign the designated signature box in ink",
                "At least one signature field requires a handwritten signature on the printed document or verification of your signature.",
            ),
            "de": (
                "Dokument ausdrucken und im Unterschriftsfeld unterschreiben",
                "Mindestens ein Unterschriftsfeld ist für die eigenhändige Unterschrift auf dem Ausdruck vorgesehen.",
            ),
            "fr": (
                "Imprimer et signer le cadre de signature à l'encre",
                "Au moins une zone de signature nécessite une signature manuscrite sur le document imprimé.",
            ),
            "ar": (
                "طباعة الوثيقة والتوقيع بخط اليد في خانة التوقيع المخصصة",
                "تتطلب الاستمارة توقيعاً يدوياً على النسخة المطبوعة في الخانة المحددة قبل تقديمها.",
            ),
        }[lang]
        items.append(
            {
                "id": "manual_signature_required",
                "title": sig_copy[0],
                "description": sig_copy[1],
                "category": "signature",
                "required": True,
            }
        )

    # 3. Landlord / housing provider counter-signature & rental proof
    if has_landlord_party:
        landlord_copy = {
            "en": (
                "Obtain landlord / housing provider confirmation & signature",
                "Have your landlord or housing provider (Wohnungsgeber / Vermieter) verify their section and sign the document.",
            ),
            "de": (
                "Bestätigung und Unterschrift des Wohnungsgebers / Vermieters einholen",
                "Lassen Sie den Abschnitt des Wohnungsgebers bzw. Vermieters prüfen und unterschreiben.",
            ),
            "fr": (
                "Obtenir la confirmation et la signature du bailleur / logeur",
                "Faites vérifier et signer la section réservée au propriétaire ou bailleur.",
            ),
            "ar": (
                "الحصول على تأكيد وتوقيع المؤجر أو مقدم السكن (Wohnungsgeber / Vermieter)",
                "اطلب من المؤجر أو مالك السكن مراجعة القسم الخاص به والتوقيع عليه.",
            ),
        }[lang]
        items.append(
            {
                "id": "landlord_counter_signature",
                "title": landlord_copy[0],
                "description": landlord_copy[1],
                "category": "attachment",
                "required": True,
            }
        )

    # 4. Bank / IBAN verification when bank fields are present
    if has_bank_fields:
        bank_copy = {
            "en": (
                "Double-check IBAN and BIC digits against your bank statement",
                "Verify every digit of the IBAN and BIC so payments or direct debits are not rejected.",
            ),
            "de": (
                "IBAN und BIC anhand Ihres Kontoauszugs abgleichen",
                "Prüfen Sie jede Ziffer der IBAN und den BIC-Code, damit Zahlungen oder Lastschriften fehlerfrei ausgeführt werden.",
            ),
            "fr": (
                "Vérifier les chiffres de l'IBAN et du BIC avec votre RIB",
                "Contrôlez chaque caractère de l'IBAN et du BIC pour éviter tout rejet bancaire.",
            ),
            "ar": (
                "مطابقة أرقام الحساب البنكي (IBAN و BIC) مع كشف الحساب",
                "تأكد من صحة جميع الأرقام والرموز البنكية لتجنب رفض التحويلات المالية.",
            ),
        }[lang]
        items.append(
            {
                "id": "verify_bank_details",
                "title": bank_copy[0],
                "description": bank_copy[1],
                "category": "verification",
                "required": True,
            }
        )

    # 5. Official ID / supporting document reminder
    id_copy = {
        "en": (
            "Prepare valid Passport or National ID for all listed persons",
            "Authorities commonly require an official identity document (Reisepass, Personalausweis, or Aufenthaltstitel) when submitting this form.",
        ),
        "de": (
            "Gültigen Reisepass oder Personalausweis bereithalten",
            "Bei der Vorlage bei der Behörde wird in der Regel ein gültiges Ausweisdokument aller genannten Personen benötigt.",
        ),
        "fr": (
            "Préparer un passeport ou une pièce d'identité en cours de validité",
            "Une pièce d'identité officielle est généralement demandée lors du dépôt du dossier auprès de l'administration.",
        ),
        "ar": (
            "تجهيز جواز سفر ساري المفعول أو بطاقة الهوية لجميع الأشخاص المذكورين",
            "تطلب الجهات الرسمية عادةً إبراز وثيقة هوية سارية عند تقديم هذه الاستمارة.",
        ),
    }[lang]
    items.append(
        {
            "id": "identity_document_check",
            "title": id_copy[0],
            "description": id_copy[1],
            "category": "attachment",
            "required": True,
        }
    )

    return items
