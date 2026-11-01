import logging
from typing import Any

from sqlalchemy.orm import Session

from app.questions.repositories import QuestionRepository

logger = logging.getLogger(__name__)


def _tr(
    *,
    en: tuple[str, str, str],
    de: tuple[str, str, str],
    fr: tuple[str, str, str],
    ar: tuple[str, str, str],
    tr: tuple[str, str, str],
    uk: tuple[str, str, str],
    es: tuple[str, str, str],
    ru: tuple[str, str, str],
) -> dict[str, dict[str, str]]:
    """Build 8-language translation dictionary from (text, placeholder, help_text) tuples."""
    pairs = {
        "en": en,
        "de": de,
        "fr": fr,
        "ar": ar,
        "tr": tr,
        "uk": uk,
        "es": es,
        "ru": ru,
    }
    return {
        lang: {"text": val[0], "placeholder": val[1], "help_text": val[2]}
        for lang, val in pairs.items()
    }


# Core catalog definitions seed data across all 8 launch languages
SEED_QUESTIONS: list[dict[str, Any]] = [
    {
        "question_key": "personal.first_name",
        "field_type": "person_name",
        "purpose": "collect_value",
        "domain": "personal",
        "translations": _tr(
            en=(
                "What is your first name?",
                "First name",
                "Please provide your first name as listed on your identity document.",
            ),
            de=(
                "Wie lautet Ihr Vorname?",
                "Vorname",
                "Bitte geben Sie Ihren Vornamen so an, wie er im Ausweis steht.",
            ),
            fr=(
                "Quel est votre prénom ?",
                "Prénom",
                "Veuillez indiquer votre prénom tel qu'il figure sur votre pièce d'identité.",
            ),
            ar=(
                "ما هو اسمك الأول؟",
                "الاسم الأول",
                "يرجى تقديم اسمك الأول كما هو موضح في وثيقة هويتك.",
            ),
            tr=(
                "Adınız nedir?",
                "Adınız",
                "Lütfen kimlik veya pasaportunuzda yazdığı şekilde adınızı girin.",
            ),
            uk=(
                "Яке ваше ім'я?",
                "Ім'я",
                "Вкажіть ваше ім'я латиницею, як у закордонному паспорті.",
            ),
            es=(
                "¿Cuál es su nombre de pila?",
                "Nombre",
                "Indique su nombre tal como aparece en su pasaporte o documento de identidad.",
            ),
            ru=(
                "Как ваше имя?",
                "Имя",
                "Укажите ваше имя так, как оно записано в загранпаспорте или удостоверении личности.",
            ),
        ),
    },
    {
        "question_key": "personal.last_name",
        "field_type": "person_name",
        "purpose": "collect_value",
        "domain": "personal",
        "translations": _tr(
            en=(
                "What is your last name?",
                "Last name",
                "Please provide your family name as listed on your identity document.",
            ),
            de=(
                "Wie lautet Ihr Nachname?",
                "Nachname",
                "Bitte geben Sie Ihren Nachnamen so an, wie er im Ausweis steht.",
            ),
            fr=(
                "Quel est votre nom de famille ?",
                "Nom de famille",
                "Veuillez indiquer votre nom de famille tel qu'il figure sur votre pièce d'identité.",
            ),
            ar=(
                "ما هو اسم عائلتك؟",
                "اسم العائلة",
                "يرجى تقديم اسم عائلتك كما هو موضح في وثيقة هويتك.",
            ),
            tr=(
                "Soyadınız nedir?",
                "Soyadınız",
                "Lütfen pasaport veya kimliğinizde yer alan soyadınızı girin.",
            ),
            uk=(
                "Яке ваше прізвище?",
                "Прізвище",
                "Вкажіть ваше прізвище так, як у закордонному паспорті.",
            ),
            es=(
                "¿Cuáles son sus apellidos?",
                "Apellidos",
                "Indique su apellido tal como figura en su documento de identidad.",
            ),
            ru=(
                "Какая у вас фамилия?",
                "Фамилия",
                "Укажите вашу фамилию точно так, как в загранпаспорте.",
            ),
        ),
    },
    {
        "question_key": "personal.date_of_birth",
        "field_type": "date",
        "purpose": "collect_value",
        "domain": "personal",
        "translations": _tr(
            en=(
                "What is your date of birth?",
                "YYYY-MM-DD",
                "Please select or type your birth date.",
            ),
            de=(
                "Wie lautet Ihr Geburtsdatum?",
                "TT.MM.JJJJ",
                "Bitte wählen Sie Ihr Geburtsdatum aus oder geben Sie es ein.",
            ),
            fr=(
                "Quelle est votre date de naissance ?",
                "JJ/MM/AAAA",
                "Veuillez sélectionner ou saisir votre date de naissance.",
            ),
            ar=(
                "ما هو تاريخ ميلادك؟",
                "YYYY-MM-DD",
                "يرجى تحديد أو كتابة تاريخ ميلادك.",
            ),
            tr=(
                "Doğum tarihiniz nedir?",
                "GG.AA.YYYY",
                "Lütfen doğum tarihinizi seçin veya yazın.",
            ),
            uk=(
                "Яка ваша дата народження?",
                "ДД.ММ.РРРР",
                "Будь ласка, оберіть або введіть дату народження.",
            ),
            es=(
                "¿Cuál es su fecha de nacimiento?",
                "DD/MM/AAAA",
                "Seleccione o escriba su fecha de nacimiento.",
            ),
            ru=(
                "Какова ваша дата рождения?",
                "ДД.ММ.ГГГГ",
                "Пожалуйста, выберите или введите дату рождения.",
            ),
        ),
    },
    {
        "question_key": "contact.email",
        "field_type": "email",
        "purpose": "collect_value",
        "domain": "contact",
        "translations": _tr(
            en=(
                "What is your email address?",
                "name@example.com",
                "We will use this email address for form notifications if requested.",
            ),
            de=(
                "Wie lautet Ihre E-Mail-Adresse?",
                "name@example.de",
                "Bitte geben Sie eine gültige E-Mail-Adresse für Rückfragen der Stelle an.",
            ),
            fr=(
                "Quelle est votre adresse e-mail ?",
                "nom@example.com",
                "Indiquez une adresse e-mail valide pour d'éventuelles questions.",
            ),
            ar=(
                "ما هو عنوان بريدك الإلكتروني؟",
                "name@example.com",
                "يرجى إدخال عنوان بريد إلكتروني صالح للتواصل الرسمي.",
            ),
            tr=(
                "E-posta adresiniz nedir?",
                "isim@ornek.com",
                "Kurumun sizinle iletişime geçebileceği geçerli bir e-posta adresi girin.",
            ),
            uk=(
                "Яка ваша адреса електронної пошти?",
                "name@example.com",
                "Вкажіть дійсну електронну адресу для офіційного зв'язку.",
            ),
            es=(
                "¿Cuál es su correo electrónico?",
                "nombre@ejemplo.com",
                "Introduzca un correo electrónico válido para posibles consultas.",
            ),
            ru=(
                "Какой у вас адрес электронной почты?",
                "name@example.com",
                "Укажите действующий адрес электронной почты для обратной связи.",
            ),
        ),
    },
    {
        "question_key": "contact.phone",
        "field_type": "phone",
        "purpose": "collect_value",
        "domain": "contact",
        "translations": _tr(
            en=(
                "What is your phone number?",
                "+49 170 1234567",
                "Please enter your phone number with international prefix.",
            ),
            de=(
                "Wie lautet Ihre Telefonnummer?",
                "+49 170 1234567",
                "Bitte geben Sie Ihre Telefonnummer mit internationaler Vorwahl an.",
            ),
            fr=(
                "Quel est votre numéro de téléphone ?",
                "+49 170 1234567",
                "Veuillez saisir votre numéro de téléphone avec indicatif international.",
            ),
            ar=(
                "ما هو رقم هاتفك؟",
                "+49 170 1234567",
                "يرجى إدخال رقم هاتفك مع رمز الاتصال الدولي.",
            ),
            tr=(
                "Telefon numaranız nedir?",
                "+49 170 1234567",
                "Lütfen ülke koduyla birlikte telefon numaranızı girin.",
            ),
            uk=(
                "Який ваш номер телефону?",
                "+49 170 1234567",
                "Введіть номер телефону з міжнародним кодом країни.",
            ),
            es=(
                "¿Cuál es su número de teléfono?",
                "+49 170 1234567",
                "Escriba su número de teléfono incluyendo el prefijo internacional.",
            ),
            ru=(
                "Какой у вас номер телефона?",
                "+49 170 1234567",
                "Введите номер телефона с международным кодом страны.",
            ),
        ),
    },
    {
        "question_key": "address.street",
        "field_type": "string",
        "purpose": "collect_value",
        "domain": "address",
        "translations": _tr(
            en=(
                "What is your street and house number?",
                "Hauptstr. 12",
                "Please provide your German street name and house number.",
            ),
            de=(
                "Wie lautet Ihre Straße und Hausnummer?",
                "Hauptstr. 12",
                "Bitte geben Sie Ihre Straße und Hausnummer an.",
            ),
            fr=(
                "Quels sont votre rue et numéro de maison ?",
                "Hauptstr. 12",
                "Veuillez indiquer le nom de la rue et le numéro.",
            ),
            ar=(
                "ما هو اسم الشارع ورقم المنزل؟",
                "Hauptstr. 12",
                "يرجى كتابة اسم الشارع ورقم المبنى بالأحرف اللاتينية كما في العقد.",
            ),
            tr=(
                "Sokak adı ve bina numaranız nedir?",
                "Hauptstr. 12",
                "Kira sözleşmenizde yer alan sokak adını ve kapı numarasını girin.",
            ),
            uk=(
                "Яка ваша вулиця та номер будинку?",
                "Hauptstr. 12",
                "Вкажіть назву вулиці та номер будинку згідно з договором оренди.",
            ),
            es=(
                "¿Cuál es su calle y número de portal?",
                "Hauptstr. 12",
                "Indique el nombre de la calle y el número tal como figuran en su contrato.",
            ),
            ru=(
                "Какая у вас улица и номер дома?",
                "Hauptstr. 12",
                "Укажите название улицы и номер дома латиницей, как в договоре аренды.",
            ),
        ),
    },
    {
        "question_key": "address.postal_code",
        "field_type": "string",
        "purpose": "collect_value",
        "domain": "address",
        "translations": _tr(
            en=(
                "What is your 5-digit postal code (PLZ)?",
                "10115",
                "Enter the 5-digit German Postleitzahl.",
            ),
            de=(
                "Wie lautet Ihre Postleitzahl (PLZ)?",
                "10115",
                "Bitte geben Sie Ihre fünfstellige Postleitzahl an.",
            ),
            fr=(
                "Quel est votre code postal (PLZ) ?",
                "10115",
                "Veuillez saisir le code postal allemand à 5 chiffres.",
            ),
            ar=(
                "ما هو الرمز البريدي (PLZ)؟",
                "10115",
                "يرجى إدخال الرمز البريدي الألماني المكون من 5 أرقام.",
            ),
            tr=(
                "Posta kodunuz (PLZ) nedir?",
                "10115",
                "Lütfen 5 haneli Alman posta kodunuzu (Postleitzahl) girin.",
            ),
            uk=(
                "Який ваш поштовий індекс (PLZ)?",
                "10115",
                "Введіть 5-значний поштовий індекс у Німеччині.",
            ),
            es=(
                "¿Cuál es su código postal (PLZ)?",
                "10115",
                "Introduzca el código postal alemán de 5 dígitos.",
            ),
            ru=(
                "Какой у вас почтовый индекс (PLZ)?",
                "10115",
                "Введите 5-значный почтовый индекс Германии.",
            ),
        ),
    },
    {
        "question_key": "address.city",
        "field_type": "string",
        "purpose": "collect_value",
        "domain": "address",
        "translations": _tr(
            en=(
                "What is your city or municipality (Wohnort)?",
                "Berlin",
                "Provide the name of the city or municipality.",
            ),
            de=(
                "Wie lautet Ihr Wohnort?",
                "Berlin",
                "Bitte geben Sie Ihren Wohnort bzw. Ihre Gemeinde an.",
            ),
            fr=(
                "Quelle est votre ville de résidence ?",
                "Berlin",
                "Indiquez le nom de la ville ou de la commune.",
            ),
            ar=(
                "ما هي مدينة الإقامة (Wohnort)؟",
                "Berlin",
                "يرجى كتابة اسم المدينة أو البلدية في ألمانيا.",
            ),
            tr=(
                "Yaşadığınız şehir veya belediye (Wohnort) nedir?",
                "Berlin",
                "İkamet ettiğiniz şehrin adını girin.",
            ),
            uk=(
                "У якому місті чи громаді (Wohnort) ви проживаєте?",
                "Berlin",
                "Вкажіть назву міста або громади проживання.",
            ),
            es=(
                "¿En qué ciudad o municipio (Wohnort) reside?",
                "Berlin",
                "Indique el nombre de la ciudad o municipio.",
            ),
            ru=(
                "В каком городе или общине (Wohnort) вы проживаете?",
                "Berlin",
                "Укажите название города или муниципалитета.",
            ),
        ),
    },
    {
        "question_key": "address.country",
        "field_type": "country",
        "purpose": "collect_value",
        "domain": "address",
        "translations": _tr(
            en=(
                "What is your country of residence?",
                "Germany",
                "Provide your current country of residence.",
            ),
            de=(
                "In welchem Land wohnen Sie?",
                "Deutschland",
                "Bitte geben Sie Ihr Wohnortland an.",
            ),
            fr=(
                "Quel est votre pays de résidence ?",
                "Allemagne",
                "Veuillez indiquer votre pays de résidence.",
            ),
            ar=(
                "ما هو بلد إقامتك؟",
                "ألمانيا",
                "يرجى تحديد بلد إقامتك الحالي.",
            ),
            tr=(
                "İkamet ettiğiniz ülke hangisidir?",
                "Almanya",
                "Lütfen mevcut ikamet ülkenizi belirtin.",
            ),
            uk=(
                "Яка ваша країна проживання?",
                "Німеччина",
                "Вкажіть країну вашого поточного проживання.",
            ),
            es=(
                "¿Cuál es su país de residencia?",
                "Alemania",
                "Indique su país de residencia actual.",
            ),
            ru=(
                "В какой стране вы проживаете?",
                "Германия",
                "Укажите страну вашего текущего проживания.",
            ),
        ),
    },
    {
        "question_key": "civil_status.marital_status",
        "field_type": "single_choice",
        "purpose": "collect_value",
        "domain": "civil_status",
        "translations": _tr(
            en=(
                "What is your marital status?",
                "Select status",
                "Select your current legal marital status.",
            ),
            de=(
                "Wie lautet Ihr Familienstand?",
                "Status auswählen",
                "Bitte wählen Sie Ihren aktuellen gesetzlichen Familienstand aus.",
            ),
            fr=(
                "Quel est votre état civil ?",
                "Sélectionner statut",
                "Veuillez sélectionner votre état civil actuel.",
            ),
            ar=(
                "ما هي حالتك الاجتماعية؟",
                "اختر الحالة",
                "يرجى اختيار حالتك الاجتماعية القانونية الحالية.",
            ),
            tr=(
                "Medeni durumunuz nedir?",
                "Durum seçin",
                "Mevcut resmi medeni durumunuzu seçin.",
            ),
            uk=(
                "Який ваш сімейний стан?",
                "Оберіть стан",
                "Оберіть ваш поточний офіційний сімейний стан.",
            ),
            es=(
                "¿Cuál es su estado civil?",
                "Seleccionar estado",
                "Seleccione su estado civil legal actual.",
            ),
            ru=(
                "Каково ваше семейное положение?",
                "Выберите статус",
                "Выберите ваше текущее официальное семейное положение.",
            ),
        ),
    },
    {
        "question_key": "finance.monthly_income",
        "field_type": "money",
        "purpose": "collect_value",
        "domain": "finance",
        "translations": _tr(
            en=(
                "What is your net monthly household income (in EUR)?",
                "2400 EUR",
                "Enter your average monthly net income including currency (e.g. 2400 EUR).",
            ),
            de=(
                "Wie hoch ist Ihr monatliches Nettoeinkommen (in EUR)?",
                "2400 EUR",
                "Bitte geben Sie Ihr durchschnittliches monatliches Nettoeinkommen mit Währung an.",
            ),
            fr=(
                "Quel est votre revenu mensuel net (en EUR) ?",
                "2400 EUR",
                "Indiquez votre revenu mensuel net moyen avec la devise (ex. 2400 EUR).",
            ),
            ar=(
                "ما هو صافي دخلك الشهري (باليورو EUR)؟",
                "2400 EUR",
                "يرجى كتابة متوسط صافي الدخل الشهري مع العملة (مثال: 2400 EUR).",
            ),
            tr=(
                "Aylık net geliriniz nedir (EUR cinsinden)?",
                "2400 EUR",
                "Ortalama aylık net gelirinizi para birimiyle yazın (ör. 2400 EUR).",
            ),
            uk=(
                "Який ваш щомісячний чистий дохід (в EUR)?",
                "2400 EUR",
                "Вкажіть середній чистий місячний дохід із валютою (напр., 2400 EUR).",
            ),
            es=(
                "¿Cuál es su ingreso mensual neto (en EUR)?",
                "2400 EUR",
                "Indique su ingreso neto mensual medio con moneda (ej. 2400 EUR).",
            ),
            ru=(
                "Каков ваш ежемесячный чистый доход (в EUR)?",
                "2400 EUR",
                "Укажите средний чистый ежемесячный доход с валютой (напр., 2400 EUR).",
            ),
        ),
    },
    {
        "question_key": "finance.iban",
        "field_type": "string",
        "purpose": "collect_value",
        "domain": "finance",
        "translations": _tr(
            en=(
                "What is your IBAN bank account number?",
                "DE89 3704 0044 0532 0130 00",
                "Enter the IBAN from your bank card or banking app.",
            ),
            de=(
                "Wie lautet Ihre IBAN?",
                "DE89 3704 0044 0532 0130 00",
                "Bitte geben Sie die IBAN Ihres Bankkontos ein.",
            ),
            fr=(
                "Quel est votre numéro de compte IBAN ?",
                "DE89 3704 0044 0532 0130 00",
                "Saisissez le code IBAN figurant sur votre relevé bancaire.",
            ),
            ar=(
                "ما هو رقم الحساب البنكي الدولي (IBAN)؟",
                "DE89 3704 0044 0532 0130 00",
                "يرجى إدخال رقم IBAN الموجود في تطبيق البنك أو البطاقة البنكية.",
            ),
            tr=(
                "IBAN banka hesap numaranız nedir?",
                "DE89 3704 0044 0532 0130 00",
                "Banka kartınızda veya mobil bankacılıkta yazan IBAN numarasını girin.",
            ),
            uk=(
                "Який ваш міжнародний номер банківського рахунку (IBAN)?",
                "DE89 3704 0044 0532 0130 00",
                "Введіть номер IBAN із банківського додатка або картки.",
            ),
            es=(
                "¿Cuál es su número de cuenta bancaria IBAN?",
                "DE89 3704 0044 0532 0130 00",
                "Introduzca el IBAN que aparece en su aplicación o tarjeta bancaria.",
            ),
            ru=(
                "Какой у вас номер банковского счета IBAN?",
                "DE89 3704 0044 0532 0130 00",
                "Введите номер IBAN из вашего банковского приложения или карты.",
            ),
        ),
    },
    {
        "question_key": "residence.move_in_date",
        "field_type": "date",
        "purpose": "collect_value",
        "domain": "residence",
        "translations": _tr(
            en=(
                "On what date did you move into the apartment (Einzugsdatum)?",
                "YYYY-MM-DD",
                "Enter the actual move-in date confirmed by your landlord.",
            ),
            de=(
                "An welchem Datum sind Sie in die Wohnung eingezogen (Einzugsdatum)?",
                "TT.MM.JJJJ",
                "Bitte geben Sie das tatsächliche Einzugsdatum laut Wohnungsgeber an.",
            ),
            fr=(
                "À quelle date avez-vous emménagé dans le logement (Einzugsdatum) ?",
                "JJ/MM/AAAA",
                "Indiquez la date réelle d'emménagement confirmée par le bailleur.",
            ),
            ar=(
                "ما هو تاريخ الانتقال الفعلي إلى السكن (Einzugsdatum)؟",
                "YYYY-MM-DD",
                "أدخل تاريخ السكن الفعلي المؤكد من المؤجر وليس تاريخ توقيع العقد.",
            ),
            tr=(
                "Daireye taşınma tarihiniz (Einzugsdatum) nedir?",
                "GG.AA.YYYY",
                "Ev sahibinizin onayladığı fiili taşınma tarihini girin.",
            ),
            uk=(
                "Яка дата фактичного заселення у квартиру (Einzugsdatum)?",
                "ДД.ММ.РРРР",
                "Вкажіть фактичну дату в'їзду, підтверджену орендодавцем.",
            ),
            es=(
                "¿En qué fecha se mudó a la vivienda (Einzugsdatum)?",
                "DD/MM/AAAA",
                "Indique la fecha real de entrada en la vivienda confirmada por el arrendador.",
            ),
            ru=(
                "Какова фактическая дата въезда в квартиру (Einzugsdatum)?",
                "ДД.ММ.ГГГГ",
                "Укажите фактическую дату заселения, подтвержденную арендодателем.",
            ),
        ),
    },
    {
        "question_key": "residence.landlord_name",
        "field_type": "person_name",
        "purpose": "collect_value",
        "domain": "residence",
        "translations": _tr(
            en=(
                "What is the full name of your landlord or property company (Wohnungsgeber)?",
                "Max Mustermann / Hausverwaltung GmbH",
                "Found at the top of your rental contract (Mietvertrag).",
            ),
            de=(
                "Wie lautet der Name des Wohnungsgebers (Vermieter / Hausverwaltung)?",
                "Max Mustermann",
                "Den Namen finden Sie auf der ersten Seite Ihres Mietvertrags.",
            ),
            fr=(
                "Quel est le nom complet du bailleur ou de la régie (Wohnungsgeber) ?",
                "Max Mustermann",
                "Ce nom figure sur la première page de votre contrat de bail.",
            ),
            ar=(
                "ما هو الاسم الكامل للمؤجر أو شركة العقارات (Wohnungsgeber)؟",
                "Max Mustermann",
                "تجد هذا الاسم في الصفحة الأولى من عقد الإيجار (Mietvertrag).",
            ),
            tr=(
                "Ev sahibinin veya yönetim şirketinin (Wohnungsgeber) tam adı nedir?",
                "Max Mustermann",
                "Kira sözleşmenizin (Mietvertrag) ilk sayfasında yer alır.",
            ),
            uk=(
                "Яке повне ім'я або назва орендодавця (Wohnungsgeber)?",
                "Max Mustermann",
                "Зазначено на першій сторінці вашого договору оренди (Mietvertrag).",
            ),
            es=(
                "¿Cuál es el nombre completo del arrendador o administración (Wohnungsgeber)?",
                "Max Mustermann",
                "Aparece en la primera página de su contrato de alquiler (Mietvertrag).",
            ),
            ru=(
                "Как зовут арендодателя или управляющую компанию (Wohnungsgeber)?",
                "Max Mustermann",
                "Имя указано на первой странице договора аренды (Mietvertrag).",
            ),
        ),
    },
    {
        "question_key": "identity.nationality",
        "field_type": "country",
        "purpose": "collect_value",
        "domain": "identity",
        "translations": _tr(
            en=(
                "What is your nationality / citizenship (Staatsangehörigkeit)?",
                "e.g. Morocco, Turkey, Ukraine",
                "Enter your citizenship as shown on your passport.",
            ),
            de=(
                "Welche Staatsangehörigkeit besitzen Sie?",
                "z.B. Deutsch, Türkisch, Ukrainisch",
                "Bitte geben Sie Ihre Staatsangehörigkeit laut Reisepass an.",
            ),
            fr=(
                "Quelle est votre nationalité (Staatsangehörigkeit) ?",
                "ex. Maroc, France",
                "Indiquez la nationalité figurant sur votre passeport.",
            ),
            ar=(
                "ما هي جنسيتك (Staatsangehörigkeit)؟",
                "مثال: المغرب، سوريا",
                "يرجى كتابة الجنسية كما هي مدونة في جواز السفر.",
            ),
            tr=(
                "Uyruğunuz / vatandaşlığınız (Staatsangehörigkeit) nedir?",
                "ör. Türkiye",
                "Pasaportunuzda belirtilen vatandaşlığınızı girin.",
            ),
            uk=(
                "Яке ваше громадянство (Staatsangehörigkeit)?",
                "напр., Україна",
                "Вкажіть громадянство згідно з вашим паспортом.",
            ),
            es=(
                "¿Cuál es su nacionalidad (Staatsangehörigkeit)?",
                "ej. España, Colombia",
                "Indique la nacionalidad que consta en su pasaporte.",
            ),
            ru=(
                "Какое у вас гражданство (Staatsangehörigkeit)?",
                "напр., Казахстан, Украина",
                "Укажите гражданство согласно вашему паспорту.",
            ),
        ),
    },
    {
        "question_key": "identity.tax_id",
        "field_type": "string",
        "purpose": "collect_value",
        "domain": "identity",
        "translations": _tr(
            en=(
                "What is your 11-digit German Tax ID (Steuer-Identifikationsnummer)?",
                "12 345 678 901",
                "Found on the letter from the Bundeszentralamt für Steuern or on your payslip.",
            ),
            de=(
                "Wie lautet Ihre elfstellige Steuer-Identifikationsnummer (Steuer-ID)?",
                "12 345 678 901",
                "Sie finden diese auf dem Schreiben des Bundeszentralamts für Steuern.",
            ),
            fr=(
                "Quel est votre numéro d'identification fiscale allemand à 11 chiffres (Steuer-ID) ?",
                "12 345 678 901",
                "Il figure sur le courrier du Bundeszentralamt für Steuern ou votre fiche de paie.",
            ),
            ar=(
                "ما هو رقم التعريف الضريبي الألماني المكون من 11 رقماً (Steuer-ID)؟",
                "12 345 678 901",
                "تجد هذا الرقم في رسالة مصلحة الضرائب الفيدرالية أو في كشف الراتب.",
            ),
            tr=(
                "11 haneli Alman Vergi Kimlik Numaranız (Steuer-ID) nedir?",
                "12 345 678 901",
                "Vergi dairesinden gelen mektupta veya maaş bordronuzda yer alır.",
            ),
            uk=(
                "Який ваш 11-значний податковий номер у Німеччині (Steuer-ID)?",
                "12 345 678 901",
                "Вказаний у листі від Bundeszentralamt für Steuern або в розрахунковому листку.",
            ),
            es=(
                "¿Cuál es su número de identificación fiscal alemán de 11 dígitos (Steuer-ID)?",
                "12 345 678 901",
                "Aparece en la carta del Bundeszentralamt für Steuern o en su nómina.",
            ),
            ru=(
                "Какой у вас 11-значный налоговый идентификационный номер в Германии (Steuer-ID)?",
                "12 345 678 901",
                "Указан в письме от Bundeszentralamt für Steuern или в расчетном листке.",
            ),
        ),
    },
    {
        "question_key": "family.child_first_name",
        "field_type": "person_name",
        "purpose": "collect_value",
        "domain": "family",
        "translations": _tr(
            en=(
                "What is the child's first name?",
                "Child's first name",
                "Enter the child's first name exactly as shown on the birth certificate.",
            ),
            de=(
                "Wie lautet der Vorname des Kindes?",
                "Vorname des Kindes",
                "Bitte geben Sie den Vornamen des Kindes laut Geburtsurkunde an.",
            ),
            fr=(
                "Quel est le prénom de l'enfant ?",
                "Prénom de l'enfant",
                "Indiquez le prénom de l'enfant tel qu'il figure sur l'acte de naissance.",
            ),
            ar=(
                "ما هو الاسم الأول للطفل؟",
                "الاسم الأول للطفل",
                "يرجى كتابة الاسم الأول للطفل كما هو مدون في شهادة الميلاد.",
            ),
            tr=(
                "Çocuğun adı nedir?",
                "Çocuğun adı",
                "Çocuğun doğum belgesinde yazan adını girin.",
            ),
            uk=(
                "Яке ім'я дитини?",
                "Ім'я дитини",
                "Вкажіть ім'я дитини згідно зі свідоцтвом про народження.",
            ),
            es=(
                "¿Cuál es el nombre del niño o de la niña?",
                "Nombre del menor",
                "Escriba el nombre tal como consta en el certificado de nacimiento.",
            ),
            ru=(
                "Как зовут ребенка (имя)?",
                "Имя ребенка",
                "Укажите имя ребенка согласно свидетельству о рождении.",
            ),
        ),
    },
    {
        "question_key": "family.child_birth_date",
        "field_type": "date",
        "purpose": "collect_value",
        "domain": "family",
        "translations": _tr(
            en=(
                "What is the child's date of birth?",
                "YYYY-MM-DD",
                "Enter the birth date from the child's birth certificate.",
            ),
            de=(
                "Wie lautet das Geburtsdatum des Kindes?",
                "TT.MM.JJJJ",
                "Bitte geben Sie das Geburtsdatum laut Geburtsurkunde ein.",
            ),
            fr=(
                "Quelle est la date de naissance de l'enfant ?",
                "JJ/MM/AAAA",
                "Saisissez la date figurant sur l'acte de naissance.",
            ),
            ar=(
                "ما هو تاريخ ميلاد الطفل؟",
                "YYYY-MM-DD",
                "أدخل تاريخ ميلاد الطفل كما في شهادة الميلاد.",
            ),
            tr=(
                "Çocuğun doğum tarihi nedir?",
                "GG.AA.YYYY",
                "Doğum belgesinde yer alan tarihi girin.",
            ),
            uk=(
                "Яка дата народження дитини?",
                "ДД.ММ.РРРР",
                "Введіть дату народження зі свідоцтва про народження.",
            ),
            es=(
                "¿Cuál es la fecha de nacimiento del menor?",
                "DD/MM/AAAA",
                "Introduzca la fecha del certificado de nacimiento.",
            ),
            ru=(
                "Какова дата рождения ребенка?",
                "ДД.ММ.ГГГГ",
                "Введите дату рождения согласно свидетельству о рождении.",
            ),
        ),
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
                if existing_trans.review_status != "approved":
                    existing_trans.text = trans_data["text"]
                    existing_trans.placeholder = trans_data["placeholder"]
                    existing_trans.help_text = trans_data["help_text"]
                    existing_trans.source = "fixture"
                    existing_trans.review_status = "approved"
                    db.commit()
