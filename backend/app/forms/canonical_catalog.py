"""Canonical Key Semantic Catalog for AI Schema Auto-Mapping & Vault Pre-Fill.

Provides rich semantic metadata and multilingual anchor descriptions for standard
administrative form fields (civil registry, residence registration, taxation, banking).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanonicalFieldDefinition:
    key: str
    label_en: str
    label_de: str
    description: str
    expected_type: str
    synonyms_de: list[str]
    synonyms_en: list[str]

    @property
    def semantic_text(self) -> str:
        """Returns rich text representation for dense vector embedding."""
        de_str = ", ".join(self.synonyms_de)
        en_str = ", ".join(self.synonyms_en)
        return (
            f"{self.label_de} ({self.label_en}) - {self.description}. "
            f"German terms: {de_str}. English terms: {en_str}."
        )


CANONICAL_SCHEMA_CATALOG: list[CanonicalFieldDefinition] = [
    CanonicalFieldDefinition(
        key="personal.first_name",
        label_en="First Name / Given Name",
        label_de="Vorname",
        description="First or given name of the applicant as stated in official passport or ID card",
        expected_type="string",
        synonyms_de=[
            "vorname",
            "vornamen",
            "rufname",
            "vor- und zuname",
            "antragsteller vorname",
        ],
        synonyms_en=[
            "first name",
            "given name",
            "forename",
            "first names",
            "applicant first name",
        ],
    ),
    CanonicalFieldDefinition(
        key="personal.last_name",
        label_en="Last Name / Surname / Family Name",
        label_de="Familienname / Nachname",
        description="Surname, family name, or last name of the applicant",
        expected_type="string",
        synonyms_de=["familienname", "nachname", "name", "geburtsname", "zuname"],
        synonyms_en=[
            "last name",
            "surname",
            "family name",
            "maiden name",
            "legal surname",
        ],
    ),
    CanonicalFieldDefinition(
        key="personal.full_name",
        label_en="Full Legal Name",
        label_de="Vollständiger Name",
        description="Full name combining first and last name in a single field",
        expected_type="string",
        synonyms_de=[
            "vor- und nachname",
            "vollständiger name",
            "name, vorname",
            "name der antragstellenden person",
        ],
        synonyms_en=["full name", "applicant full name", "complete name", "legal name"],
    ),
    CanonicalFieldDefinition(
        key="person.date_of_birth",
        label_en="Date of Birth",
        label_de="Geburtsdatum",
        description="Official birth date in DD.MM.YYYY or ISO 8601 format",
        expected_type="date",
        synonyms_de=["geburtsdatum", "geburtstag", "geboren am", "tag der geburt"],
        synonyms_en=["date of birth", "birth date", "dob", "born on", "birthdate"],
    ),
    CanonicalFieldDefinition(
        key="personal.place_of_birth",
        label_en="Place of Birth / City of Birth",
        label_de="Geburtsort",
        description="Municipality, town, or city where the applicant was born",
        expected_type="string",
        synonyms_de=["geburtsort", "geboren in", "ort der geburt", "geburtsgemeinde"],
        synonyms_en=["place of birth", "birth place", "city of birth", "town of birth"],
    ),
    CanonicalFieldDefinition(
        key="personal.nationality",
        label_en="Nationality / Citizenship",
        label_de="Staatsangehörigkeit",
        description="Country of citizenship or official nationality",
        expected_type="string",
        synonyms_de=[
            "staatsangehörigkeit",
            "staatsbuergerschaft",
            "nationalität",
            "staatsangehoerigkeit",
        ],
        synonyms_en=[
            "nationality",
            "citizenship",
            "country of citizenship",
            "state nationality",
        ],
    ),
    CanonicalFieldDefinition(
        key="contact.email",
        label_en="Email Address",
        label_de="E-Mail-Adresse",
        description="Electronic mail address for official notifications and confirmations",
        expected_type="string",
        synonyms_de=[
            "e-mail",
            "e-mail-adresse",
            "email",
            "elektronische post",
            "kontakt-email",
        ],
        synonyms_en=[
            "email",
            "email address",
            "e-mail",
            "electronic mail",
            "contact email",
        ],
    ),
    CanonicalFieldDefinition(
        key="contact.phone",
        label_en="Phone Number / Mobile",
        label_de="Telefonnummer",
        description="Telephone or cellular mobile number including country or area code",
        expected_type="string",
        synonyms_de=[
            "telefon",
            "telefonnummer",
            "mobiltelefon",
            "rufnummer",
            "handynummer",
            "festnetz",
        ],
        synonyms_en=[
            "phone",
            "phone number",
            "mobile",
            "telephone",
            "cell phone",
            "contact number",
        ],
    ),
    CanonicalFieldDefinition(
        key="address.street_and_number",
        label_en="Street and House Number",
        label_de="Straße und Hausnummer",
        description="Residential street name, house number, and apartment or building suffix",
        expected_type="string",
        synonyms_de=[
            "straße und hausnummer",
            "straße",
            "hausnummer",
            "str.",
            "anschrift",
            "wohnanschrift",
        ],
        synonyms_en=[
            "street and number",
            "street address",
            "house number",
            "street name",
            "address line 1",
        ],
    ),
    CanonicalFieldDefinition(
        key="address.postal_code",
        label_en="Postal Code / ZIP",
        label_de="Postleitzahl",
        description="5-digit German postal code (PLZ) or international postal code",
        expected_type="string",
        synonyms_de=[
            "postleitzahl",
            "plz",
            "postleitzahl des wohnortes",
            "plz wohnort",
        ],
        synonyms_en=["postal code", "postcode", "zip", "zip code", "postal area"],
    ),
    CanonicalFieldDefinition(
        key="address.city",
        label_en="City / Town / Municipality",
        label_de="Wohnort / Gemeinde",
        description="Municipality, town, or city of residence",
        expected_type="string",
        synonyms_de=[
            "wohnort",
            "gemeinde",
            "stadt",
            "ort",
            "wohngemeinde",
            "ortschaft",
        ],
        synonyms_en=["city", "town", "municipality", "city of residence", "locality"],
    ),
    CanonicalFieldDefinition(
        key="address.country",
        label_en="Country of Residence",
        label_de="Land / Staat",
        description="Country of permanent or current residential address",
        expected_type="string",
        synonyms_de=["land", "staat", "wohnland", "wohnsitzstaat"],
        synonyms_en=["country", "nation", "country of residence", "state of residence"],
    ),
    CanonicalFieldDefinition(
        key="financial.iban",
        label_en="Bank Account IBAN",
        label_de="IBAN / Bankverbindung",
        description="International Bank Account Number for direct debit, fees, or refunds",
        expected_type="string",
        synonyms_de=[
            "iban",
            "bankverbindung",
            "kontonummer",
            "debitorenkonto",
            "girokonto",
            "sepa-iban",
        ],
        synonyms_en=[
            "iban",
            "bank account",
            "bank details",
            "account number",
            "international bank account",
        ],
    ),
    CanonicalFieldDefinition(
        key="residence.move_in_date",
        label_en="Move-in Date / Registration Date",
        label_de="Einzugsdatum",
        description="Official move-in date into the registered apartment or residence",
        expected_type="date",
        synonyms_de=[
            "einzugsdatum",
            "bezugsdatum",
            "eingezogen am",
            "datum des einzugs",
            "umzugsdatum",
        ],
        synonyms_en=[
            "move-in date",
            "date of move in",
            "date of occupancy",
            "move in date",
            "moving date",
        ],
    ),
    CanonicalFieldDefinition(
        key="signature.applicant",
        label_en="Applicant Signature",
        label_de="Unterschrift der antragstellenden Person",
        description="Biometric or handwritten signature confirming application accuracy",
        expected_type="signature",
        synonyms_de=[
            "unterschrift",
            "unterschrift der antragstellenden person",
            "datum und unterschrift",
            "eigenhändige unterschrift",
        ],
        synonyms_en=[
            "signature",
            "applicant signature",
            "signature of applicant",
            "sign here",
        ],
    ),
]


def get_canonical_catalog_by_key() -> dict[str, CanonicalFieldDefinition]:
    """Returns catalog mapped by technical key."""
    return {defn.key: defn for defn in CANONICAL_SCHEMA_CATALOG}
