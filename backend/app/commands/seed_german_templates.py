import json
import logging
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.forms.models import FormTemplate, FormVersion
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.questions.seed import seed_catalog

logger = logging.getLogger(__name__)


def _field_def(
    *,
    key: str,
    field_type: str,
    question_key: str,
    label_de: str,
    label_en: str,
    max_len: int = 80,
    required: bool = True,
    confirm: bool = False,
) -> dict[str, Any]:
    config: dict[str, Any] = {"requiresConfirmation": confirm}
    if field_type in ("string", "person_name"):
        config["maxLength"] = max_len
    elif field_type == "money":
        config["allowedCurrencies"] = ["EUR"]
        config["minimum"] = 0

    return {
        "key": key,
        "field_type": field_type,
        "question_key": question_key,
        "label_de": label_de,
        "label_en": label_en,
        "pdf_max_length": max_len,
        "required": required,
        "configuration": config,
    }


GERMAN_TEMPLATE_SPECS: list[dict[str, Any]] = [
    {
        "key": "de-anmeldung",
        "name": "Anmeldung bei der Meldebehörde",
        "subtitle_de": "Wohnsitzanmeldung gemäß § 17 Bundesmeldegesetz (BMG)",
        "description": "City residence registration (Anmeldung) for newcomers moving into an apartment in Germany.",
        "submission_method": "in_person",
        "required_documents": [
            "Valid passport or national ID card (Personalausweis / Reisepass)",
            "Signed Landlord Confirmation of Residence (Wohnungsgeberbestätigung, § 19 BMG)",
            "Visa / residence permit page (if non-EU citizen)",
        ],
        "instructions": "Print and sign the completed Anmeldung PDF, attach the signed Wohnungsgeberbestätigung from your landlord, and bring your passport to your booked Bürgeramt / Einwohnermeldeamt appointment within 14 days of moving in.",
        "fields": [
            _field_def(
                key="first_name",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="Vorname(n) (Rufname)",
                label_en="First Name(s)",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="last_name",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="Familienname (Nachname)",
                label_en="Family Name (Last Name)",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="date_of_birth",
                field_type="date",
                question_key="personal.date_of_birth",
                label_de="Geburtsdatum (TT.MM.JJJJ)",
                label_en="Date of Birth",
                max_len=10,
                confirm=True,
            ),
            _field_def(
                key="nationality",
                field_type="country",
                question_key="identity.nationality",
                label_de="Staatsangehörigkeit",
                label_en="Nationality",
                max_len=40,
            ),
            _field_def(
                key="move_in_date",
                field_type="date",
                question_key="residence.move_in_date",
                label_de="Tag des Einzugs",
                label_en="Move-in Date",
                max_len=10,
                confirm=True,
            ),
            _field_def(
                key="street",
                field_type="string",
                question_key="address.street",
                label_de="Neue Wohnung: Straße und Hausnummer",
                label_en="New Street and House Number",
                max_len=80,
                confirm=True,
            ),
            _field_def(
                key="postal_code",
                field_type="string",
                question_key="address.postal_code",
                label_de="Postleitzahl (PLZ)",
                label_en="Postal Code (PLZ)",
                max_len=10,
            ),
            _field_def(
                key="city",
                field_type="string",
                question_key="address.city",
                label_de="Gemeinde / Wohnort",
                label_en="City / Municipality",
                max_len=50,
            ),
        ],
    },
    {
        "key": "de-wohnungsgeberbestaetigung",
        "name": "Wohnungsgeberbestätigung (§ 19 BMG)",
        "subtitle_de": "Bestätigung des Wohnungsgebers zur Vorlage bei der Meldebehörde",
        "description": "Mandatory landlord residence confirmation required for city registration (Anmeldung).",
        "submission_method": "print_and_sign",
        "required_documents": [
            "Signed lease agreement (Mietvertrag) showing move-in date and apartment address",
            "Landlord / property manager full name and postal address",
        ],
        "instructions": "Download the pre-filled PDF and send it to your landlord or housing provider (Wohnungsgeber) to sign and date. Present the signed original together with your Anmeldung at your Bürgeramt appointment.",
        "fields": [
            _field_def(
                key="landlord_name",
                field_type="person_name",
                question_key="residence.landlord_name",
                label_de="Name und Anschrift des Wohnungsgebers",
                label_en="Landlord Full Name / Company",
                max_len=80,
                confirm=True,
            ),
            _field_def(
                key="move_in_date",
                field_type="date",
                question_key="residence.move_in_date",
                label_de="Tag des tatsächlichen Einzugs",
                label_en="Actual Move-in Date",
                max_len=10,
                confirm=True,
            ),
            _field_def(
                key="street",
                field_type="string",
                question_key="address.street",
                label_de="Anschrift der Wohnung: Straße und Hausnummer",
                label_en="Apartment Street & Number",
                max_len=80,
                confirm=True,
            ),
            _field_def(
                key="postal_code",
                field_type="string",
                question_key="address.postal_code",
                label_de="Postleitzahl (PLZ)",
                label_en="Postal Code",
                max_len=10,
            ),
            _field_def(
                key="city",
                field_type="string",
                question_key="address.city",
                label_de="Ort / Gemeinde",
                label_en="City",
                max_len=50,
            ),
            _field_def(
                key="first_name",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="Meldepflichtige Person: Vorname",
                label_en="Tenant First Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="last_name",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="Meldepflichtige Person: Nachname",
                label_en="Tenant Last Name",
                max_len=60,
                confirm=True,
            ),
        ],
    },
    {
        "key": "de-kindergeld-kg1",
        "name": "Antrag auf Kindergeld (KG1)",
        "subtitle_de": "Hauptantrag für die Familienkasse — Grunddaten",
        "description": "German child benefit main intake form (Familienkasse KG1) with Tax-ID and IBAN.",
        "fields": [
            _field_def(
                key="first_name",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="Antragstellende Person: Vorname",
                label_en="Applicant First Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="last_name",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="Antragstellende Person: Familienname",
                label_en="Applicant Last Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="tax_id",
                field_type="string",
                question_key="identity.tax_id",
                label_de="Steuerliche Identifikationsnummer (11-stellig)",
                label_en="German Tax ID (11 digits)",
                max_len=20,
                confirm=True,
            ),
            _field_def(
                key="street",
                field_type="string",
                question_key="address.street",
                label_de="Straße und Hausnummer",
                label_en="Street and House Number",
                max_len=80,
            ),
            _field_def(
                key="postal_code",
                field_type="string",
                question_key="address.postal_code",
                label_de="Postleitzahl",
                label_en="Postal Code",
                max_len=10,
            ),
            _field_def(
                key="city",
                field_type="string",
                question_key="address.city",
                label_de="Wohnort",
                label_en="City",
                max_len=50,
            ),
            _field_def(
                key="child_first_name",
                field_type="person_name",
                question_key="family.child_first_name",
                label_de="Vorname des Kindes",
                label_en="Child's First Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="child_birth_date",
                field_type="date",
                question_key="family.child_birth_date",
                label_de="Geburtsdatum des Kindes",
                label_en="Child's Date of Birth",
                max_len=10,
                confirm=True,
            ),
            _field_def(
                key="iban",
                field_type="string",
                question_key="finance.iban",
                label_de="IBAN für die Auszahlung",
                label_en="Payout IBAN",
                max_len=34,
                confirm=True,
            ),
        ],
    },
    {
        "key": "de-sepa-lastschriftmandat",
        "name": "SEPA-Lastschriftmandat",
        "subtitle_de": "Wiederkehrende Zahlungen — Einzugsermächtigung",
        "description": "Standard German SEPA Direct Debit mandate for utilities, rent, internet, or municipal fees.",
        "fields": [
            _field_def(
                key="first_name",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="Kontoinhaber/in: Vorname",
                label_en="Account Holder First Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="last_name",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="Kontoinhaber/in: Nachname",
                label_en="Account Holder Last Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="street",
                field_type="string",
                question_key="address.street",
                label_de="Straße und Hausnummer",
                label_en="Street and House Number",
                max_len=80,
            ),
            _field_def(
                key="postal_code",
                field_type="string",
                question_key="address.postal_code",
                label_de="Postleitzahl (PLZ)",
                label_en="Postal Code",
                max_len=10,
            ),
            _field_def(
                key="city",
                field_type="string",
                question_key="address.city",
                label_de="Ort",
                label_en="City",
                max_len=50,
            ),
            _field_def(
                key="country",
                field_type="country",
                question_key="address.country",
                label_de="Land",
                label_en="Country",
                max_len=40,
            ),
            _field_def(
                key="iban",
                field_type="string",
                question_key="finance.iban",
                label_de="IBAN des Zahlungskontos",
                label_en="IBAN",
                max_len=34,
                confirm=True,
            ),
            _field_def(
                key="email",
                field_type="email",
                question_key="contact.email",
                label_de="E-Mail für Vorabankündigung",
                label_en="Email for SEPA Pre-Notification",
                max_len=80,
                required=False,
            ),
        ],
    },
    {
        "key": "de-mieterselbstauskunft",
        "name": "Mieterselbstauskunft",
        "subtitle_de": "Selbstauskunft für Mietinteressenten zur Wohnungsbewerbung",
        "description": "German tenant self-disclosure form requested by landlords and housing agencies during apartment viewings.",
        "fields": [
            _field_def(
                key="first_name",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="Vorname",
                label_en="First Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="last_name",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="Nachname",
                label_en="Last Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="date_of_birth",
                field_type="date",
                question_key="personal.date_of_birth",
                label_de="Geburtsdatum",
                label_en="Date of Birth",
                max_len=10,
            ),
            _field_def(
                key="phone",
                field_type="phone",
                question_key="contact.phone",
                label_de="Telefonnummer",
                label_en="Phone Number",
                max_len=30,
            ),
            _field_def(
                key="email",
                field_type="email",
                question_key="contact.email",
                label_de="E-Mail-Adresse",
                label_en="Email Address",
                max_len=80,
            ),
            _field_def(
                key="street",
                field_type="string",
                question_key="address.street",
                label_de="Derzeitige Anschrift: Straße und Nr.",
                label_en="Current Street & Number",
                max_len=80,
            ),
            _field_def(
                key="postal_code",
                field_type="string",
                question_key="address.postal_code",
                label_de="Derzeitige PLZ",
                label_en="Current Postal Code",
                max_len=10,
            ),
            _field_def(
                key="city",
                field_type="string",
                question_key="address.city",
                label_de="Derzeitiger Wohnort",
                label_en="Current City",
                max_len=50,
            ),
            _field_def(
                key="monthly_income",
                field_type="money",
                question_key="finance.monthly_income",
                label_de="Monatliches Haushaltsnettoeinkommen (EUR)",
                label_en="Monthly Net Income (EUR)",
                max_len=25,
                confirm=True,
            ),
        ],
    },
    {
        "key": "de-krankenkasse-mitgliedsantrag",
        "name": "Mitgliedsantrag Gesetzliche Krankenkasse",
        "subtitle_de": "Aufnahme in die gesetzliche Kranken- und Pflegeversicherung",
        "description": "Statutory German health insurance enrollment form (Krankenkasse) for employees, students, and newcomers.",
        "fields": [
            _field_def(
                key="first_name",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="Vorname",
                label_en="First Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="last_name",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="Nachname",
                label_en="Last Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="date_of_birth",
                field_type="date",
                question_key="personal.date_of_birth",
                label_de="Geburtsdatum",
                label_en="Date of Birth",
                max_len=10,
                confirm=True,
            ),
            _field_def(
                key="nationality",
                field_type="country",
                question_key="identity.nationality",
                label_de="Staatsangehörigkeit",
                label_en="Nationality",
                max_len=40,
            ),
            _field_def(
                key="street",
                field_type="string",
                question_key="address.street",
                label_de="Straße und Hausnummer",
                label_en="Street and House Number",
                max_len=80,
            ),
            _field_def(
                key="postal_code",
                field_type="string",
                question_key="address.postal_code",
                label_de="Postleitzahl",
                label_en="Postal Code",
                max_len=10,
            ),
            _field_def(
                key="city",
                field_type="string",
                question_key="address.city",
                label_de="Wohnort",
                label_en="City",
                max_len=50,
            ),
            _field_def(
                key="phone",
                field_type="phone",
                question_key="contact.phone",
                label_de="Telefonnummer für Rückfragen",
                label_en="Phone Number",
                max_len=30,
                required=False,
            ),
            _field_def(
                key="email",
                field_type="email",
                question_key="contact.email",
                label_de="E-Mail-Adresse",
                label_en="Email Address",
                max_len=80,
            ),
        ],
    },
    {
        "key": "de-wohngeld-kurzantrag",
        "name": "Wohngeld-Kurzantrag (Mietzuschuss)",
        "subtitle_de": "Antrag auf Mietzuschuss nach dem Wohngeldgesetz (WoGG)",
        "description": "German municipal housing allowance intake form (Wohngeld Mietzuschuss) for low-to-moderate income households.",
        "fields": [
            _field_def(
                key="first_name",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="Vorname der wohngeldberechtigten Person",
                label_en="Applicant First Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="last_name",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="Familienname",
                label_en="Applicant Last Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="date_of_birth",
                field_type="date",
                question_key="personal.date_of_birth",
                label_de="Geburtsdatum",
                label_en="Date of Birth",
                max_len=10,
            ),
            _field_def(
                key="street",
                field_type="string",
                question_key="address.street",
                label_de="Anschrift des Wohnraums: Straße und Nr.",
                label_en="Apartment Street & Number",
                max_len=80,
            ),
            _field_def(
                key="postal_code",
                field_type="string",
                question_key="address.postal_code",
                label_de="Postleitzahl",
                label_en="Postal Code",
                max_len=10,
            ),
            _field_def(
                key="city",
                field_type="string",
                question_key="address.city",
                label_de="Gemeinde / Stadt",
                label_en="City",
                max_len=50,
            ),
            _field_def(
                key="monthly_income",
                field_type="money",
                question_key="finance.monthly_income",
                label_de="Monatliches Haushaltsnettoeinkommen (EUR)",
                label_en="Monthly Net Income (EUR)",
                max_len=25,
                confirm=True,
            ),
            _field_def(
                key="iban",
                field_type="string",
                question_key="finance.iban",
                label_de="IBAN für die Wohngeldauszahlung",
                label_en="IBAN for Payment",
                max_len=34,
                confirm=True,
            ),
        ],
    },
    {
        "key": "de-elterngeld-basisdaten",
        "name": "Antrag auf Elterngeld — Basisdaten",
        "subtitle_de": "Grundangaben nach dem Bundeselterngeld- und Elternzeitgesetz (BEEG)",
        "description": "Parental allowance core intake sheet (Elterngeld) for new parents living in Germany.",
        "fields": [
            _field_def(
                key="first_name",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="Antragstellender Elternteil: Vorname",
                label_en="Parent First Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="last_name",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="Antragstellender Elternteil: Nachname",
                label_en="Parent Last Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="date_of_birth",
                field_type="date",
                question_key="personal.date_of_birth",
                label_de="Geburtsdatum des Elternteils",
                label_en="Parent Date of Birth",
                max_len=10,
            ),
            _field_def(
                key="tax_id",
                field_type="string",
                question_key="identity.tax_id",
                label_de="Steuer-Identifikationsnummer (11-stellig)",
                label_en="Parent Tax ID",
                max_len=20,
                confirm=True,
            ),
            _field_def(
                key="child_first_name",
                field_type="person_name",
                question_key="family.child_first_name",
                label_de="Vorname des Kindes",
                label_en="Child's First Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="child_birth_date",
                field_type="date",
                question_key="family.child_birth_date",
                label_de="Geburtsdatum des Kindes",
                label_en="Child's Date of Birth",
                max_len=10,
                confirm=True,
            ),
            _field_def(
                key="iban",
                field_type="string",
                question_key="finance.iban",
                label_de="IBAN des Auszahlungskontos",
                label_en="Payout IBAN",
                max_len=34,
                confirm=True,
            ),
        ],
    },
    {
        "key": "de-kita-anmeldung",
        "name": "Anmeldung Kindertagesbetreuung (Kita)",
        "subtitle_de": "Bedarfsanzeige / Vormerkung für einen Betreuungsplatz",
        "description": "Municipal daycare and kindergarten registration form (Kita-Anmeldung) for families in Germany.",
        "fields": [
            _field_def(
                key="child_first_name",
                field_type="person_name",
                question_key="family.child_first_name",
                label_de="Vorname des Kindes",
                label_en="Child's First Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="child_birth_date",
                field_type="date",
                question_key="family.child_birth_date",
                label_de="Geburtsdatum des Kindes",
                label_en="Child's Date of Birth",
                max_len=10,
                confirm=True,
            ),
            _field_def(
                key="first_name",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="Sorgeberechtigte Person: Vorname",
                label_en="Parent/Guardian First Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="last_name",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="Sorgeberechtigte Person: Nachname",
                label_en="Parent/Guardian Last Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="street",
                field_type="string",
                question_key="address.street",
                label_de="Wohnanschrift: Straße und Hausnummer",
                label_en="Home Street and Number",
                max_len=80,
            ),
            _field_def(
                key="postal_code",
                field_type="string",
                question_key="address.postal_code",
                label_de="Postleitzahl",
                label_en="Postal Code",
                max_len=10,
            ),
            _field_def(
                key="city",
                field_type="string",
                question_key="address.city",
                label_de="Wohnort",
                label_en="City",
                max_len=50,
            ),
            _field_def(
                key="phone",
                field_type="phone",
                question_key="contact.phone",
                label_de="Telefonnummer",
                label_en="Phone Number",
                max_len=30,
            ),
            _field_def(
                key="email",
                field_type="email",
                question_key="contact.email",
                label_de="E-Mail-Adresse",
                label_en="Email Address",
                max_len=80,
            ),
        ],
    },
    {
        "key": "de-rundfunkbeitrag-anmeldung",
        "name": "Anmeldung zum Rundfunkbeitrag",
        "subtitle_de": "Wohnungsanmeldung beim ARD ZDF Deutschlandradio Beitragsservice",
        "description": "German household broadcasting fee registration form (Rundfunkbeitrag) after moving into an apartment.",
        "fields": [
            _field_def(
                key="first_name",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="Vorname",
                label_en="First Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="last_name",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="Nachname",
                label_en="Last Name",
                max_len=60,
                confirm=True,
            ),
            _field_def(
                key="date_of_birth",
                field_type="date",
                question_key="personal.date_of_birth",
                label_de="Geburtsdatum",
                label_en="Date of Birth",
                max_len=10,
            ),
            _field_def(
                key="street",
                field_type="string",
                question_key="address.street",
                label_de="Straße und Hausnummer der Wohnung",
                label_en="Apartment Street & Number",
                max_len=80,
            ),
            _field_def(
                key="postal_code",
                field_type="string",
                question_key="address.postal_code",
                label_de="Postleitzahl",
                label_en="Postal Code",
                max_len=10,
            ),
            _field_def(
                key="city",
                field_type="string",
                question_key="address.city",
                label_de="Ort",
                label_en="City",
                max_len=50,
            ),
            _field_def(
                key="move_in_date",
                field_type="date",
                question_key="residence.move_in_date",
                label_de="Beginn des Innehabens der Wohnung",
                label_en="Move-in Date",
                max_len=10,
            ),
            _field_def(
                key="iban",
                field_type="string",
                question_key="finance.iban",
                label_de="IBAN (SEPA-Lastschrift)",
                label_en="IBAN",
                max_len=34,
                required=False,
                confirm=True,
            ),
        ],
    },
    {
        "key": "de-aufenthaltstitel",
        "name": "Antrag auf Erteilung / Verlängerung eines Aufenthaltstitels",
        "subtitle_de": "Aufenthaltsgesetz (AufenthG) — Erteilung / Verlängerung (Blaue Karte EU, Aufenthaltserlaubnis)",
        "description": "Official German Residence Permit & EU Blue Card application for international professionals and relocation.",
        "submission_method": "in_person",
        "required_documents": [
            "Valid passport (with current entry visa or previous residence permit)",
            "Signed employment contract (Arbeitsvertrag) & Declaration of Employment (Erklärung zum Beschäftigungsverhältnis)",
            "Recognized university degree (anabin / ZAB) if applying for EU Blue Card",
            "City registration certificate (Anmeldebestätigung) & rental contract",
            "Biometric passport photo & proof of German health insurance coverage",
        ],
        "instructions": "Review all confirmed personal, passport, and employer details, download the completed PDF, sign the applicant declaration, and upload or bring the signed form with the supporting originals to your local Ausländerbehörde (Foreigners' Authority) appointment.",
        "fields": [
            _field_def(
                key="family_name",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="2. Familienname",
                label_en="Family name / Surname",
                max_len=60,
                required=True,
                confirm=True,
            ),
            _field_def(
                key="birth_name",
                field_type="person_name",
                question_key="personal.birth_name",
                label_de="Geburtsname",
                label_en="Name at birth",
                max_len=60,
                required=False,
            ),
            _field_def(
                key="first_names",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="3. Vornamen",
                label_en="First names / Given names",
                max_len=60,
                required=True,
                confirm=True,
            ),
            _field_def(
                key="date_of_birth",
                field_type="date",
                question_key="person.date_of_birth",
                label_de="4. Geburtsdatum",
                label_en="Date of birth (YYYY-MM-DD)",
                max_len=10,
                required=True,
            ),
            _field_def(
                key="place_of_birth",
                field_type="string",
                question_key="person.place_of_birth",
                label_de="5. Geburtsort",
                label_en="Place of birth",
                max_len=60,
                required=True,
            ),
            _field_def(
                key="nationality",
                field_type="country",
                question_key="person.nationality",
                label_de="6. Staatsangehörigkeit",
                label_en="Nationality (ISO 3166-1 alpha-2)",
                max_len=2,
                required=True,
            ),
            _field_def(
                key="marital_status",
                field_type="string",
                question_key="person.marital_status",
                label_de="9. Familienstand",
                label_en="Marital status",
                max_len=40,
                required=True,
            ),
            _field_def(
                key="gender",
                field_type="string",
                question_key="person.gender",
                label_de="10. Geschlecht",
                label_en="Gender",
                max_len=20,
                required=True,
            ),
            _field_def(
                key="current_address",
                field_type="string",
                question_key="residence.current_address",
                label_de="7. Derzeitige Anschrift (Wohnort, Straße, Hausnummer)",
                label_en="Current residential address in Germany",
                max_len=120,
                required=True,
            ),
            _field_def(
                key="contact_email",
                field_type="email",
                question_key="contact.email",
                label_de="8. E-Mail-Adresse",
                label_en="Contact email address",
                max_len=80,
                required=True,
            ),
            _field_def(
                key="contact_phone",
                field_type="string",
                question_key="contact.phone",
                label_de="Telefonnummer",
                label_en="Contact telephone number",
                max_len=30,
                required=False,
            ),
            _field_def(
                key="purpose_of_stay",
                field_type="string",
                question_key="immigration.purpose_of_stay",
                label_de="1. Zweck des Aufenthalts (z. B. Erwerbstätigkeit, Blaue Karte EU)",
                label_en="Purpose of stay (e.g. Employment, EU Blue Card, Family reunion)",
                max_len=120,
                required=True,
            ),
        ],
    },
    {
        "key": "eu-schengen-visa",
        "name": "Application for Schengen Visa (Harmonised EU Form)",
        "subtitle_de": "Harmonised European Union Schengen Visa (Regulation EC No 810/2009)",
        "description": "Standard European Union Schengen visa application for short-term stay, tourism, business, and study across all 29 Schengen member states.",
        "source_language": "en",
        "supported_output_languages": ["en", "de", "fr"],
        "fields": [
            _field_def(
                key="surname",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="1. Nachname (Familienname)",
                label_en="1. Surname (Family name)",
                max_len=60,
                required=True,
                confirm=True,
            ),
            _field_def(
                key="first_names",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="3. Vornamen (Rufnamen)",
                label_en="3. First name(s) (Given name(s))",
                max_len=60,
                required=True,
                confirm=True,
            ),
            _field_def(
                key="date_of_birth",
                field_type="date",
                question_key="person.date_of_birth",
                label_de="4. Geburtsdatum (JJJJ-MM-TT)",
                label_en="4. Date of birth (YYYY-MM-DD)",
                max_len=10,
                required=True,
            ),
            _field_def(
                key="place_of_birth",
                field_type="string",
                question_key="person.place_of_birth",
                label_de="5. Geburtsort",
                label_en="5. Place of birth",
                max_len=60,
                required=True,
            ),
            _field_def(
                key="current_nationality",
                field_type="country",
                question_key="person.nationality",
                label_de="7. Derzeitige Staatsangehörigkeit",
                label_en="7. Current nationality",
                max_len=2,
                required=True,
            ),
            _field_def(
                key="gender",
                field_type="string",
                question_key="person.gender",
                label_de="8. Geschlecht",
                label_en="8. Sex (Male / Female)",
                max_len=20,
                required=True,
            ),
            _field_def(
                key="marital_status",
                field_type="string",
                question_key="person.marital_status",
                label_de="9. Zivilstand",
                label_en="9. Civil status (Single / Married / Divorced)",
                max_len=30,
                required=True,
            ),
            _field_def(
                key="home_address",
                field_type="string",
                question_key="residence.current_address",
                label_de="17. Wohnanschrift des Antragstellers",
                label_en="17. Applicant's home address",
                max_len=120,
                required=True,
            ),
            _field_def(
                key="contact_email",
                field_type="email",
                question_key="contact.email",
                label_de="E-Mail-Adresse",
                label_en="Email address",
                max_len=80,
                required=True,
            ),
            _field_def(
                key="contact_phone",
                field_type="string",
                question_key="contact.phone",
                label_de="Telefonnummer",
                label_en="Telephone number(s)",
                max_len=30,
                required=False,
            ),
            _field_def(
                key="purpose_of_journey",
                field_type="string",
                question_key="immigration.purpose_of_stay",
                label_de="21. Hauptzweck(e) der Reise (z. B. Tourismus, Geschäftlich)",
                label_en="21. Main purpose(s) of the journey (e.g. Tourism, Business)",
                max_len=120,
                required=True,
            ),
        ],
    },
    {
        "key": "us-immigration-intake",
        "name": "US Immigration & Professional Relocation Intake",
        "subtitle_de": "USCIS / DOS International Talent Standard Intake Form",
        "description": "Standard immigration and employment intake form for international employees and relocation candidates moving to the United States.",
        "source_language": "en",
        "supported_output_languages": ["en"],
        "fields": [
            _field_def(
                key="family_name",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="Nachname",
                label_en="Legal Family Name / Surname",
                max_len=60,
                required=True,
                confirm=True,
            ),
            _field_def(
                key="given_name",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="Vorname",
                label_en="Given Name / First Name",
                max_len=60,
                required=True,
                confirm=True,
            ),
            _field_def(
                key="date_of_birth",
                field_type="date",
                question_key="person.date_of_birth",
                label_de="Geburtsdatum",
                label_en="Date of Birth (YYYY-MM-DD)",
                max_len=10,
                required=True,
            ),
            _field_def(
                key="country_of_citizenship",
                field_type="country",
                question_key="person.nationality",
                label_de="Staatsangehörigkeit",
                label_en="Country of Citizenship",
                max_len=2,
                required=True,
            ),
            _field_def(
                key="current_address",
                field_type="string",
                question_key="residence.current_address",
                label_de="Wohnanschrift",
                label_en="Current Residential Address",
                max_len=120,
                required=True,
            ),
            _field_def(
                key="contact_email",
                field_type="email",
                question_key="contact.email",
                label_de="E-Mail-Adresse",
                label_en="Primary Contact Email",
                max_len=80,
                required=True,
            ),
            _field_def(
                key="contact_phone",
                field_type="string",
                question_key="contact.phone",
                label_de="Telefonnummer",
                label_en="Mobile Phone Number",
                max_len=30,
                required=False,
            ),
            _field_def(
                key="visa_category",
                field_type="string",
                question_key="immigration.purpose_of_stay",
                label_de="Visumkategorie / Zweck",
                label_en="Target Visa Category (e.g. H-1B, L-1, O-1, Permanent Residency)",
                max_len=100,
                required=True,
            ),
        ],
    },
    {
        "key": "uk-visas-intake",
        "name": "UK Visas & International Employee Intake",
        "subtitle_de": "UK Home Office Standard Employee Relocation Intake",
        "description": "Administrative intake form for international professionals and sponsored skilled workers relocating to the United Kingdom.",
        "source_language": "en",
        "supported_output_languages": ["en"],
        "fields": [
            _field_def(
                key="family_name",
                field_type="person_name",
                question_key="personal.last_name",
                label_de="Nachname",
                label_en="Family name / Surname",
                max_len=60,
                required=True,
                confirm=True,
            ),
            _field_def(
                key="given_names",
                field_type="person_name",
                question_key="personal.first_name",
                label_de="Vornamen",
                label_en="Given names",
                max_len=60,
                required=True,
                confirm=True,
            ),
            _field_def(
                key="date_of_birth",
                field_type="date",
                question_key="person.date_of_birth",
                label_de="Geburtsdatum",
                label_en="Date of birth (YYYY-MM-DD)",
                max_len=10,
                required=True,
            ),
            _field_def(
                key="nationality",
                field_type="country",
                question_key="person.nationality",
                label_de="Staatsangehörigkeit",
                label_en="Nationality",
                max_len=2,
                required=True,
            ),
            _field_def(
                key="current_address",
                field_type="string",
                question_key="residence.current_address",
                label_de="Wohnanschrift",
                label_en="Current home address",
                max_len=120,
                required=True,
            ),
            _field_def(
                key="contact_email",
                field_type="email",
                question_key="contact.email",
                label_de="E-Mail-Adresse",
                label_en="Contact email address",
                max_len=80,
                required=True,
            ),
            _field_def(
                key="contact_phone",
                field_type="string",
                question_key="contact.phone",
                label_de="Telefonnummer",
                label_en="Contact telephone number",
                max_len=30,
                required=False,
            ),
            _field_def(
                key="visa_route",
                field_type="string",
                question_key="immigration.purpose_of_stay",
                label_de="Visum-Kategorie",
                label_en="Immigration Route (e.g. Skilled Worker, Global Talent, Senior Specialist)",
                max_len=100,
                required=True,
            ),
        ],
    },
]


def _default_fixtures_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parents[3] / "fixtures" / "pdf",
        Path("/fixtures/pdf"),
        Path("fixtures/pdf"),
    ]
    for candidate in candidates:
        if candidate.parent.exists():
            return candidate
    return candidates[0]


def generate_german_pdf_fixtures(output_dir: Path | None = None) -> list[Path]:
    """Generate printable A4 AcroForm PDFs, .mapping.json, and .fingerprint.json for all 10 German forms."""
    target_dir = output_dir or _default_fixtures_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    width, height = A4  # 595.27559 x 841.88976 pt
    created_paths: list[Path] = []

    for spec in GERMAN_TEMPLATE_SPECS:
        pdf_key = f"{spec['key']}-v1"
        marker = f"Formular-Kennung: {pdf_key.upper()}"
        pdf_path = target_dir / f"{pdf_key}.pdf"
        mapping_path = target_dir / f"{pdf_key}.mapping.json"
        fp_path = target_dir / f"{pdf_key}.fingerprint.json"

        pdf_canvas = canvas.Canvas(str(pdf_path), pagesize=A4)

        # Header band
        pdf_canvas.setFillColor(colors.HexColor("#0F172A"))
        pdf_canvas.rect(0, height - 76, width, 76, stroke=0, fill=1)
        pdf_canvas.setFillColor(colors.white)
        title_font_size = 11.0 if len(spec["name"]) > 40 else 13.0
        pdf_canvas.setFont("Helvetica-Bold", title_font_size)
        pdf_canvas.drawString(36, height - 38, spec["name"])
        pdf_canvas.setFont("Helvetica", 8.5)
        pdf_canvas.drawString(36, height - 55, spec["subtitle_de"][:75])
        pdf_canvas.setFont("Helvetica", 8)
        pdf_canvas.drawRightString(width - 36, height - 38, marker)
        out_lang_display = (
            f"Output: {spec.get('supported_output_languages', ['EN'])[0].upper()}"
            if spec.get("source_language") == "en"
            else "Ausgabesprache: Deutsch (DE)"
        )
        pdf_canvas.drawRightString(width - 36, height - 52, out_lang_display)

        # Form fields
        acro_form = pdf_canvas.acroForm
        num_fields = len(spec["fields"])
        usable_height = (height - 110) - 75
        row_step = min(56.0, usable_height / max(num_fields, 1))
        field_h = 20 if num_fields > 9 else 22
        field_font_size = 9 if num_fields > 9 else 10
        label_font_size = 8.5 if num_fields > 9 else 9.0
        start_y = height - 105

        mapping_fields: list[dict[str, Any]] = []
        acro_names: list[str] = []

        for idx, fspec in enumerate(spec["fields"]):
            y_pos = start_y - idx * row_step
            pdf_field_name = f"{spec['key'].replace('-', '_')}_{fspec['key']}"
            acro_names.append(pdf_field_name)

            req_suffix = " *" if fspec["required"] else " (optional)"
            pdf_canvas.setFillColor(colors.HexColor("#1E293B"))
            pdf_canvas.setFont("Helvetica-Bold", label_font_size)
            field_label = (
                fspec["label_en"]
                if spec.get("source_language") == "en"
                else fspec["label_de"]
            )
            pdf_canvas.drawString(
                36, y_pos + field_h + 3, f"{idx + 1}. {field_label}{req_suffix}"
            )

            acro_form.textfield(
                name=pdf_field_name,
                x=36,
                y=y_pos,
                width=width - 72,
                height=field_h,
                value="",
                fillColor=colors.HexColor("#F8FAFC"),
                borderColor=colors.HexColor("#CBD5E1"),
                textColor=colors.HexColor("#0F172A"),
                borderWidth=1,
                fontSize=field_font_size,
            )

            mapping_fields.append(
                {
                    "fieldKey": fspec["key"],
                    "pdfFieldName": pdf_field_name,
                    "format": fspec["field_type"],
                    "maxLength": fspec["pdf_max_length"],
                    "overflow": "truncate",
                }
            )

        # Footer
        pdf_canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
        pdf_canvas.line(36, 56, width - 36, 56)
        pdf_canvas.setFillColor(colors.HexColor("#64748B"))
        pdf_canvas.setFont("Helvetica", 7.5)
        pdf_canvas.drawString(
            36,
            40,
            "Hinweis: Ausfüllhilfe-Vordruck — Bitte Angaben vor Unterschrift und Einreichung eigenverantwortlich prüfen.",
        )
        pdf_canvas.drawRightString(width - 36, 40, "Seite 1 von 1")
        pdf_canvas.save()

        mapping_payload = {
            "templateKey": pdf_key,
            "formVersionKey": f"{spec['key']}:1",
            "mappingVersion": 1,
            "strategy": "acroform",
            "fields": mapping_fields,
        }
        mapping_path.write_text(
            json.dumps(mapping_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        fingerprint_payload = {
            "templateKey": pdf_key,
            "formKey": spec["key"],
            "formVersion": 1,
            "pageCount": 1,
            "pageSizes": [
                {
                    "width": round(width, 2),
                    "height": round(height, 2),
                    "tolerance": 5.0,
                }
            ],
            "requiredAcroFormFields": acro_names,
            "optionalTextMarkers": [marker, spec["name"]],
        }
        fp_path.write_text(
            json.dumps(fingerprint_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        created_paths.append(pdf_path)

    return created_paths


def seed_german_templates(
    db: Session,
    *,
    fixtures_dir: Path | None = None,
) -> list[FormVersion]:
    """Idempotently seed the reusable 8-language catalog and Top-10 German predefined templates."""
    seed_catalog(db)

    target_dir = fixtures_dir or _default_fixtures_dir()
    first_expected_pdf = target_dir / f"{GERMAN_TEMPLATE_SPECS[0]['key']}-v1.pdf"
    if not first_expected_pdf.exists():
        generate_german_pdf_fixtures(output_dir=target_dir)

    service = FormService(db)
    published_versions: list[FormVersion] = []

    for spec in GERMAN_TEMPLATE_SPECS:
        spec_req_docs = list(spec.get("required_documents", []))
        spec_sub_method = str(spec.get("submission_method", "print_and_sign"))
        spec_instructions = spec.get(
            "instructions",
            "Review every entry carefully, download your completed PDF, sign where indicated, and submit it along with your supporting identification documents to the relevant office.",
        )

        existing_template = db.query(FormTemplate).filter_by(key=spec["key"]).first()
        if existing_template:
            if not existing_template.required_documents and spec_req_docs:
                existing_template.required_documents = spec_req_docs
            if not existing_template.instructions and spec_instructions:
                existing_template.instructions = spec_instructions
            if (
                existing_template.submission_method == "print_and_sign"
                and spec_sub_method != "print_and_sign"
            ):
                existing_template.submission_method = spec_sub_method
            db.flush()

            published_ver = (
                db.query(FormVersion)
                .filter_by(
                    form_template_id=existing_template.id,
                    status="published",
                )
                .order_by(FormVersion.version_number.desc())
                .first()
            )
            if published_ver is not None:
                published_versions.append(published_ver)
                continue
            template = existing_template
        else:
            template = service.create_template(
                key=spec["key"],
                name=spec["name"],
                description=spec["description"],
            )
            template.required_documents = spec_req_docs
            template.submission_method = spec_sub_method
            template.instructions = spec_instructions
            db.flush()

        version = service.create_draft_version(
            form_template_id=template.id,
            source_language=spec.get("source_language", "de"),
            supported_output_languages=spec.get("supported_output_languages", ["de"]),
            origin="predefined_template",
            pdf_template_key=f"{spec['key']}-v1",
        )

        for pos, fspec in enumerate(spec["fields"], start=1):
            service.add_field_to_draft(
                version.id,
                FieldCreate(
                    key=fspec["key"],
                    field_type=fspec["field_type"],
                    required=fspec["required"],
                    position=pos,
                    configuration=fspec["configuration"],
                    question_key=fspec["question_key"],
                    translations=[
                        TranslationSchema(
                            language="de",
                            label=fspec["label_de"],
                        ),
                        TranslationSchema(
                            language="en",
                            label=fspec["label_en"],
                        ),
                    ],
                ),
            )

        published = service.publish_version(version.id)
        published_versions.append(published)
        logger.info(
            "Published German template %s (v%s)", spec["key"], published.version_number
        )

    return published_versions


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    generate_german_pdf_fixtures()
    db = SessionLocal()
    try:
        versions = seed_german_templates(db)
        logger.info(
            "Successfully ensured %d published German templates.", len(versions)
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
