from typing import Any

DEFAULT_STARTER_CATEGORIES: list[dict[str, Any]] = [
    {
        "slug": "housing-residence",
        "name": "Wohnen & Meldewesen",
        "icon": "Home",
        "sort_order": 10,
        "description": "Wohnungsanmeldung, Abmeldung, Ummeldung und Vermieterbescheinigungen.",
        "translations": {
            "de": {
                "name": "Wohnen & Meldewesen",
                "description": "Wohnungsanmeldung, Abmeldung, Ummeldung und Vermieterbescheinigungen.",
            },
            "en": {
                "name": "Housing & Residence",
                "description": "Apartment registration, moving notification, and landlord confirmations.",
            },
            "ar": {
                "name": "السكن وتسجيل الإقامة",
                "description": "تسجيل السكن، تغيير العنوان، وإفادات المؤجر.",
            },
            "fr": {
                "name": "Logement & Déclaration de domicile",
                "description": "Déclaration de domicile, changement d'adresse et attestations de bailleur.",
            },
            "tr": {
                "name": "Barınma & İkamet Kaydı",
                "description": "İkametgah kaydı, adres değişikliği ve ev sahibi onay belgeleri.",
            },
            "uk": {
                "name": "Житло та реєстрація",
                "description": "Реєстрація місця проживання, зміна адреси та довідки від орендодавця.",
            },
            "es": {
                "name": "Vivienda y Empadronamiento",
                "description": "Registro de domicilio, cambio de dirección y certificados de arrendador.",
            },
            "ru": {
                "name": "Жилье и регистрация",
                "description": "Регистрация по месту жительства, смена адреса и справки от арендодателя.",
            },
        },
    },
    {
        "slug": "family-children",
        "name": "Familie, Kinder & Partnerschaft",
        "icon": "Users",
        "sort_order": 20,
        "description": "Geburtsanzeigen, Eheschließung, Kinderbetreuung und Urkunden.",
        "translations": {
            "de": {
                "name": "Familie, Kinder & Partnerschaft",
                "description": "Geburtsanzeigen, Eheschließung, Kinderbetreuung und Urkunden.",
            },
            "en": {
                "name": "Family, Children & Partnership",
                "description": "Birth registration, marriage, childcare, and official certificates.",
            },
            "ar": {
                "name": "الأسرة والأطفال والزواج",
                "description": "تسجيل المواليد، عقود الزواج، رعاية الأطفال والشهادات الرسمية.",
            },
            "fr": {
                "name": "Famille, enfants & partenariat",
                "description": "Déclaration de naissance, mariage, garde d'enfants et certificats officiels.",
            },
            "tr": {
                "name": "Aile, Çocuklar & Evlilik",
                "description": "Doğum bildirimi, evlilik, çocuk bakımı ve resmi belgeler.",
            },
            "uk": {
                "name": "Сім'я, діти та партнерство",
                "description": "Реєстрація народження, шлюб, догляд за дітьми та офіційні свідоцтва.",
            },
            "es": {
                "name": "Familia, Infancia y Pareja",
                "description": "Registro de nacimiento, matrimonio, cuidado infantil y partidas oficiales.",
            },
            "ru": {
                "name": "Семья, дети и брак",
                "description": "Регистрация рождения, брак, присмотр за детьми и официальные свидетельства.",
            },
        },
    },
    {
        "slug": "immigration-residence",
        "name": "Ausländerwesen & Aufenthalt",
        "icon": "Globe",
        "sort_order": 30,
        "description": "Aufenthaltstitel, Visumverlängerung, Einbürgerung und Verpflichtungserklärungen.",
        "translations": {
            "de": {
                "name": "Ausländerwesen & Aufenthalt",
                "description": "Aufenthaltstitel, Visumverlängerung, Einbürgerung und Verpflichtungserklärungen.",
            },
            "en": {
                "name": "Immigration & Residence",
                "description": "Residence permits, visa extensions, naturalization, and declarations of commitment.",
            },
            "ar": {
                "name": "شؤون الأجانب وتصاريح الإقامة",
                "description": "تصاريح الإقامة، تمديد التأشيرات، التجنيس، وخطابات الضمان المالي.",
            },
            "fr": {
                "name": "Affaires étrangères & Séjour",
                "description": "Titres de séjour, prolongation de visa, naturalisation et déclarations de prise en charge.",
            },
            "tr": {
                "name": "Yabancılar Dairesi & İkamet",
                "description": "İkamet tezkeresi, vize uzatma, vatandaşlık ve taahhütnameler.",
            },
            "uk": {
                "name": "Справи іноземців та перебування",
                "description": "Дозволи на проживання, продовження віз, набуття громадянства та зобов'язання.",
            },
            "es": {
                "name": "Extranjería y Residencia",
                "description": "Permisos de residencia, prórrogas de visado, nacionalidad y declaraciones de compromiso.",
            },
            "ru": {
                "name": "Миграционная служба и вид на жительство",
                "description": "Вид на жительство, продление виз, гражданство и финансовые обязательства.",
            },
        },
    },
    {
        "slug": "work-business",
        "name": "Arbeit, Steuern & Gewerbe",
        "icon": "Briefcase",
        "sort_order": 40,
        "description": "Gewerbeanmeldung, Steuerbescheinigungen, Gaststätten und Erlaubnisse.",
        "translations": {
            "de": {
                "name": "Arbeit, Steuern & Gewerbe",
                "description": "Gewerbeanmeldung, Steuerbescheinigungen, Gaststätten und Erlaubnisse.",
            },
            "en": {
                "name": "Work, Taxes & Business",
                "description": "Business registration, tax clearance certificates, catering, and trade permits.",
            },
            "ar": {
                "name": "العمل والضرائب والتجارة",
                "description": "تسجيل النشاط التجاري، الشهادات الضريبية، وتصاريح المهن.",
            },
            "fr": {
                "name": "Travail, Impôts & Entreprises",
                "description": "Déclaration d'activité professionnelle, certificats fiscaux et autorisations d'exercer.",
            },
            "tr": {
                "name": "İş, Vergi & Ticaret",
                "description": "Ticari işletme kaydı, vergi belgeleri ve mesleki izinler.",
            },
            "uk": {
                "name": "Робота, податки та підприємництво",
                "description": "Реєстрація ФОП/бізнесу, податкові довідки та комерційні дозволи.",
            },
            "es": {
                "name": "Empleo, Impuestos y Comercio",
                "description": "Alta de actividad económica, certificados tributarios y licencias comerciales.",
            },
            "ru": {
                "name": "Работа, налоги и бизнес",
                "description": "Регистрация предпринимательства, налоговые справки и лицензии.",
            },
        },
    },
    {
        "slug": "mobility-vehicles",
        "name": "Kfz & Mobilität",
        "icon": "Car",
        "sort_order": 50,
        "description": "Kfz-Zulassung, Halterwechsel, Führerscheinumtausch und Bewohnerparkausweise.",
        "translations": {
            "de": {
                "name": "Kfz, Mobilität & Führerschein",
                "description": "Kfz-Zulassung, Halterwechsel, Führerscheinumtausch und Bewohnerparkausweise.",
            },
            "en": {
                "name": "Vehicles & Mobility",
                "description": "Vehicle registration, transfer of ownership, driving license exchange, and resident parking.",
            },
            "ar": {
                "name": "المركبات ورخص القيادة",
                "description": "تسجيل المركبات، نقل الملكية، استبدال رخص القيادة، وتصاريح مواقف السكان.",
            },
            "fr": {
                "name": "Véhicules & Mobilité",
                "description": "Immatriculation de véhicules, changement de titulaire, échange de permis et stationnement résident.",
            },
            "tr": {
                "name": "Araçlar & Ulaşım",
                "description": "Araç tescili, ruhsat devri, ehliyet değişimi ve mahalle park kartı.",
            },
            "uk": {
                "name": "Авто та мобільність",
                "description": "Реєстрація авто, переоформлення, обмін посвідчень водія та паркувальні дозволи.",
            },
            "es": {
                "name": "Vehículos y Movilidad",
                "description": "Matriculación de vehículos, transferencias, canje de permisos y aparcamiento para residentes.",
            },
            "ru": {
                "name": "Транспорт и мобильность",
                "description": "Регистрация автомобилей, смена владельца, обмен водительских прав и парковочные разрешения.",
            },
        },
    },
    {
        "slug": "social-health",
        "name": "Soziales, Hilfen & Gesundheit",
        "icon": "HeartPulse",
        "sort_order": 60,
        "description": "Wohngeld, Schwerbehindertenausweis, Sozialhilfe und Gesundheitszeugnisse.",
        "translations": {
            "de": {
                "name": "Soziales, Hilfen & Gesundheit",
                "description": "Wohngeld, Schwerbehindertenausweis, Sozialhilfe und Gesundheitszeugnisse.",
            },
            "en": {
                "name": "Social Welfare & Health",
                "description": "Housing allowance (Wohngeld), disability passes, social assistance, and health certificates.",
            },
            "ar": {
                "name": "الشؤون الاجتماعية والمساعدات والصحة",
                "description": "بدل السكن (Wohngeld)، بطاقات ذوي الإعاقة، المساعدات الاجتماعية، والشهادات الصحية.",
            },
            "fr": {
                "name": "Affaires sociales & Santé",
                "description": "Allocation logement (Wohngeld), carte d'invalidité, aide sociale et certificats médicaux.",
            },
            "tr": {
                "name": "Sosyal Yardım & Sağlık",
                "description": "Kira yardımı (Wohngeld), engelli kimlik kartı, sosyal yardımlar ve sağlık raporları.",
            },
            "uk": {
                "name": "Соціальні виплати та здоров'я",
                "description": "Субсидія на житло (Wohngeld), посвідчення особи з інвалідністю та медичні довідки.",
            },
            "es": {
                "name": "Bienestar Social y Salud",
                "description": "Ayuda para vivienda (Wohngeld), tarjeta de discapacidad, asistencia social y certificados de salud.",
            },
            "ru": {
                "name": "Социальная поддержка и здоровье",
                "description": "Жилищное пособие (Wohngeld), удостоверение инвалидности, социальная помощь и справки.",
            },
        },
    },
]
