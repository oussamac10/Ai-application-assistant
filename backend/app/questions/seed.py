import logging
from typing import Any
from sqlalchemy.orm import Session
from app.questions.repositories import QuestionRepository

logger = logging.getLogger(__name__)

# Core catalog definitions seed data
SEED_QUESTIONS: list[dict[str, Any]] = [
    {
        "question_key": "personal.first_name",
        "field_type": "person_name",
        "purpose": "collect_value",
        "domain": "personal",
        "translations": {
            "en": {
                "text": "What is your first name?",
                "placeholder": "First name",
                "help_text": "Please provide your first name as listed on your identity document.",
            },
            "de": {
                "text": "Wie lautet Ihr Vorname?",
                "placeholder": "Vorname",
                "help_text": "Bitte geben Sie Ihren Vornamen so an, wie er im Ausweis steht.",
            },
            "fr": {
                "text": "Quel est votre prénom ?",
                "placeholder": "Prénom",
                "help_text": "Veuillez indiquer votre prénom tel qu'il figure sur votre pièce d'identité.",
            },
            "ar": {
                "text": "ما هو اسمك الأول؟",
                "placeholder": "الاسم الأول",
                "help_text": "يرجى تقديم اسمك الأول كما هو موضح في وثيقة هويتك.",
            },
        },
    },
    {
        "question_key": "personal.last_name",
        "field_type": "person_name",
        "purpose": "collect_value",
        "domain": "personal",
        "translations": {
            "en": {
                "text": "What is your last name?",
                "placeholder": "Last name",
                "help_text": "Please provide your family name as listed on your identity document.",
            },
            "de": {
                "text": "Wie lautet Ihr Nachname?",
                "placeholder": "Nachname",
                "help_text": "Bitte geben Sie Ihren Nachnamen so an, wie er im Ausweis steht.",
            },
            "fr": {
                "text": "Quel est votre nom de famille ?",
                "placeholder": "Nom de famille",
                "help_text": "Veuillez indiquer votre nom de famille tel qu'il figure sur votre pièce d'identité.",
            },
            "ar": {
                "text": "ما هو اسم عائلتك؟",
                "placeholder": "اسم العائلة",
                "help_text": "يرجى تقديم اسم عائلتك كما هو موضح في وثيقة هويتك.",
            },
        },
    },
    {
        "question_key": "personal.date_of_birth",
        "field_type": "date",
        "purpose": "collect_value",
        "domain": "personal",
        "translations": {
            "en": {
                "text": "What is your date of birth?",
                "placeholder": "YYYY-MM-DD",
                "help_text": "Please select or type your birth date.",
            },
            "de": {
                "text": "Wie lautet Ihr Geburtsdatum?",
                "placeholder": "TT.MM.JJJJ",
                "help_text": "Bitte wählen Sie Ihr Geburtsdatum aus oder geben Sie es ein.",
            },
            "fr": {
                "text": "Quelle est votre date de naissance ?",
                "placeholder": "JJ/MM/AAAA",
                "help_text": "Veuillez sélectionner ou saisir votre date de naissance.",
            },
            "ar": {
                "text": "ما هو تاريخ ميلادك؟",
                "placeholder": "يوم/شهر/سنة",
                "help_text": "يرجى تحديد أو كتابة تاريخ ميلادك.",
            },
        },
    },
    {
        "question_key": "contact.email",
        "field_type": "email",
        "purpose": "collect_value",
        "domain": "contact",
        "translations": {
            "en": {
                "text": "What is your email address?",
                "placeholder": "name@example.com",
                "help_text": "We will use this email address to contact you.",
            },
            "de": {
                "text": "Wie lautet Ihre E-Mail-Adresse?",
                "placeholder": "name@example.de",
                "help_text": "Wir werden diese E-Mail-Adresse verwenden, um Sie zu kontaktieren.",
            },
            "fr": {
                "text": "Quelle est votre adresse e-mail ?",
                "placeholder": "nom@example.com",
                "help_text": "Nous utiliserons cette adresse e-mail pour vous contacter.",
            },
            "ar": {
                "text": "ما هو عنوان بريدك الإلكتروني؟",
                "placeholder": "name@example.com",
                "help_text": "سنستخدم عنوان البريد الإلكتروني هذا للاتصال بك.",
            },
        },
    },
    {
        "question_key": "contact.phone",
        "field_type": "phone",
        "purpose": "collect_value",
        "domain": "contact",
        "translations": {
            "en": {
                "text": "What is your phone number?",
                "placeholder": "+1 555 123 4567",
                "help_text": "Please enter your phone number with international prefix.",
            },
            "de": {
                "text": "Wie lautet Ihre Telefonnummer?",
                "placeholder": "+49 170 1234567",
                "help_text": "Bitte geben Sie Ihre Telefonnummer mit internationaler Vorwahl an.",
            },
            "fr": {
                "text": "Quel est votre numéro de téléphone ?",
                "placeholder": "+33 6 12345678",
                "help_text": "Veuillez saisir votre numéro de téléphone avec préfixe international.",
            },
            "ar": {
                "text": "ما هو رقم هاتفك؟",
                "placeholder": "+966 50 123 4567",
                "help_text": "يرجى إدخال رقم هاتفك مع رمز الاتصال الدولي.",
            },
        },
    },
    {
        "question_key": "address.street",
        "field_type": "string",
        "purpose": "collect_value",
        "domain": "address",
        "translations": {
            "en": {
                "text": "What is your street and house number?",
                "placeholder": "Main St 123",
                "help_text": "Please provide your street address.",
            },
            "de": {
                "text": "Wie lautet Ihre Straße und Hausnummer?",
                "placeholder": "Hauptstr. 123",
                "help_text": "Bitte geben Sie Ihre Straße und Hausnummer an.",
            },
            "fr": {
                "text": "Quelle est votre rue et numéro de rue ?",
                "placeholder": "Grande Rue 123",
                "help_text": "Veuillez indiquer votre rue et numéro de maison.",
            },
            "ar": {
                "text": "ما هو اسم الشارع ورقم المنزل؟",
                "placeholder": "الشارع الرئيسي 123",
                "help_text": "يرجى تقديم عنوان الشارع الخاص بك.",
            },
        },
    },
    {
        "question_key": "address.postal_code",
        "field_type": "string",
        "purpose": "collect_value",
        "domain": "address",
        "translations": {
            "en": {
                "text": "What is your postal code?",
                "placeholder": "12345",
                "help_text": "Please enter your postal code.",
            },
            "de": {
                "text": "Wie lautet Ihre Postleitzahl?",
                "placeholder": "12345",
                "help_text": "Bitte geben Sie Ihre Postleitzahl an.",
            },
            "fr": {
                "text": "Quel est votre code postal ?",
                "placeholder": "12345",
                "help_text": "Veuillez saisir votre code postal.",
            },
            "ar": {
                "text": "ما هو الرمز البريدي الخاص بك؟",
                "placeholder": "12345",
                "help_text": "يرجى إدخال الرمز البريدي الخاص بك.",
            },
        },
    },
    {
        "question_key": "address.city",
        "field_type": "string",
        "purpose": "collect_value",
        "domain": "address",
        "translations": {
            "en": {
                "text": "What is your city of residence?",
                "placeholder": "City name",
                "help_text": "Please provide your city.",
            },
            "de": {
                "text": "Wie lautet Ihr Wohnort?",
                "placeholder": "Stadtname",
                "help_text": "Bitte geben Sie Ihren Wohnort an.",
            },
            "fr": {
                "text": "Quelle est votre ville de résidence ?",
                "placeholder": "Nom de la ville",
                "help_text": "Veuillez indiquer votre ville.",
            },
            "ar": {
                "text": "ما هي مدينة إقامتك؟",
                "placeholder": "اسم المدينة",
                "help_text": "يرجى تقديم اسم مدينتك.",
            },
        },
    },
    {
        "question_key": "address.country",
        "field_type": "country",
        "purpose": "collect_value",
        "domain": "address",
        "translations": {
            "en": {
                "text": "What is your country of residence?",
                "placeholder": "e.g. Germany",
                "help_text": "Please provide your country.",
            },
            "de": {
                "text": "In welchem Land wohnen Sie?",
                "placeholder": "z.B. Deutschland",
                "help_text": "Bitte geben Sie Ihr Wohnortland an.",
            },
            "fr": {
                "text": "Quel est votre pays de résidence ?",
                "placeholder": "ex. France",
                "help_text": "Veuillez indiquer votre pays.",
            },
            "ar": {
                "text": "ما هو بلد إقامتك؟",
                "placeholder": "مثال: ألمانيا",
                "help_text": "يرجى تقديم اسم بلد إقامتك.",
            },
        },
    },
    {
        "question_key": "civil_status.marital_status",
        "field_type": "single_choice",
        "purpose": "collect_value",
        "domain": "civil_status",
        "translations": {
            "en": {
                "text": "What is your marital status?",
                "placeholder": "Select status",
                "help_text": "Please select your current legal marital status.",
            },
            "de": {
                "text": "Wie lautet Ihr Familienstand?",
                "placeholder": "Status auswählen",
                "help_text": "Bitte wählen Sie Ihren aktuellen gesetzlichen Familienstand aus.",
            },
            "fr": {
                "text": "Quel est votre état civil ?",
                "placeholder": "Sélectionner statut",
                "help_text": "Veuillez sélectionner votre état civil actuel.",
            },
            "ar": {
                "text": "ما هي حالتك الاجتماعية؟",
                "placeholder": "اختر الحالة الاجتماعية",
                "help_text": "يرجى تحديد حالتك الاجتماعية الحالية.",
            },
        },
    },
    {
        "question_key": "finance.monthly_income",
        "field_type": "money",
        "purpose": "collect_value",
        "domain": "finance",
        "translations": {
            "en": {
                "text": "What is your net monthly income?",
                "placeholder": "Amount and currency",
                "help_text": "Please state your average net monthly income.",
            },
            "de": {
                "text": "Wie hoch ist Ihr monatliches Nettoeinkommen?",
                "placeholder": "Betrag und Währung",
                "help_text": "Bitte geben Sie Ihr durchschnittliches monatliches Nettoeinkommen an.",
            },
            "fr": {
                "text": "Quel est votre revenu mensuel net ?",
                "placeholder": "Montant et devise",
                "help_text": "Veuillez indiquer votre revenu mensuel net moyen.",
            },
            "ar": {
                "text": "ما هو صافي دخلك الشهري؟",
                "placeholder": "المبلغ والعملة",
                "help_text": "يرجى توضيح متوسط صافي دخلك الشهري.",
            },
        },
    },
]


def seed_catalog(db: Session) -> None:
    """Seed the reusable question catalog with core definitions and reviewed translations."""
    repo = QuestionRepository(db)
    for sq in SEED_QUESTIONS:
        existing_def = repo.get_definition(sq["question_key"])
        if not existing_def:
            definition = repo.create_definition(
                question_key=sq["question_key"],
                field_type=sq["field_type"],
                purpose=sq["purpose"],
                domain=sq["domain"],
            )
            logger.info("Seeded question definition: %s", sq["question_key"])
        else:
            definition = existing_def

        for lang, trans_data in sq["translations"].items():
            existing_trans = repo.get_translation(definition.id, lang)
            if not existing_trans:
                repo.create_translation(
                    definition_id=definition.id,
                    language=lang,
                    text=trans_data["text"],
                    placeholder=trans_data["placeholder"],
                    help_text=trans_data["help_text"],
                    source="fixture",
                    review_status="approved",
                )
                logger.info("Seeded translation for %s [%s]", sq["question_key"], lang)
            else:
                # Do not overwrite approved manual/fixture content, but can update pending ones if needed
                if existing_trans.review_status != "approved":
                    existing_trans.text = trans_data["text"]
                    existing_trans.placeholder = trans_data["placeholder"]
                    existing_trans.help_text = trans_data["help_text"]
                    existing_trans.source = "fixture"
                    existing_trans.review_status = "approved"
                    db.commit()
