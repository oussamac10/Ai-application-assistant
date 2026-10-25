import { PublishedForm } from "../services/apiClient";

export type FormCategoryKey =
  | "all"
  | "civil_registration"
  | "residence_housing"
  | "employment_tax"
  | "family_social"
  | "legal_declarations";

export type DocumentCategoryKey = FormCategoryKey;

export interface FormCatalogMeta {
  countryCode: string;
  countryName: string;
  authority: string;
  categoryKey: Exclude<FormCategoryKey, "all">;
  categoryLabel: string;
  formCode: string;
  estimatedMinutes: number;
  fieldCount: number;
  hasSignatureBox: boolean;
  previewSections: {
    heading: string;
    sectionTitle: string;
    fields: string[];
  }[];
}

export const DOCUMENT_CATEGORIES: {
  key: FormCategoryKey;
  label: string;
}[] = [
  { key: "all", label: "All Categories" },
  { key: "civil_registration", label: "Civil & Municipal Registration" },
  { key: "residence_housing", label: "Residence & Housing" },
  { key: "family_social", label: "Family & Social Benefits" },
  { key: "employment_tax", label: "Employment & Tax" },
  { key: "legal_declarations", label: "Declarations & Signatures" },
];

export const ISSUING_COUNTRIES: {
  code: string;
  name: string;
}[] = [
  { code: "all", name: "All Countries / Authorities" },
  { code: "INT", name: "International / Multilingual" },
  { code: "DE", name: "Germany (Deutschland)" },
  { code: "FR", name: "France (République Française)" },
  { code: "MA", name: "Morocco (المغرب / Maroc)" },
  { code: "EU", name: "European Union (EU)" },
];

const KNOWN_TEMPLATE_METADATA: Record<string, FormCatalogMeta> = {
  "basic-registration": {
    countryCode: "DE",
    countryName: "Germany / International",
    authority: "Municipal Citizens' Office (Bürgeramt)",
    categoryKey: "civil_registration",
    categoryLabel: "Civil & Municipal Registration",
    formCode: "FORM-REG-01",
    estimatedMinutes: 3,
    fieldCount: 6,
    hasSignatureBox: false,
    previewSections: [
      {
        heading: "1. Personal Identity",
        sectionTitle: "Personal Identity",
        fields: ["First Name", "Last Name", "Date of Birth"],
      },
      {
        heading: "2. Contact & Civil Status",
        sectionTitle: "Contact & Civil Status",
        fields: ["Email Address", "Country of Residence", "Marital Status"],
      },
    ],
  },
  "signature-demo": {
    countryCode: "INT",
    countryName: "International / Multilingual",
    authority: "Official Consent & Verification Registry",
    categoryKey: "legal_declarations",
    categoryLabel: "Declarations & Signatures",
    formCode: "FORM-SIG-02",
    estimatedMinutes: 2,
    fieldCount: 2,
    hasSignatureBox: true,
    previewSections: [
      {
        heading: "1. Applicant Declaration",
        sectionTitle: "Applicant Declaration",
        fields: ["Applicant Full Name"],
      },
      {
        heading: "2. Binding Signature",
        sectionTitle: "Binding Signature",
        fields: ["Digital or Handwritten Signature Box"],
      },
    ],
  },
};

export function getFormCatalogMeta(form: PublishedForm): FormCatalogMeta {
  const known = KNOWN_TEMPLATE_METADATA[form.templateKey];
  if (known) {
    return known;
  }

  // Fallback metadata inferred from sourceLanguage and name for any custom/new published template
  const src = (form.sourceLanguage || "en").toLowerCase();
  const countryCode =
    src === "de"
      ? "DE"
      : src === "fr"
        ? "FR"
        : src === "ar"
          ? "MA"
          : "INT";
  const countryName =
    countryCode === "DE"
      ? "Germany (Deutschland)"
      : countryCode === "FR"
        ? "France"
        : countryCode === "MA"
          ? "Morocco / Arabic Jurisdiction"
          : "International / Multilingual";

  return {
    countryCode,
    countryName,
    authority: "Public Administration Authority",
    categoryKey: "civil_registration",
    categoryLabel: "Civil & Municipal Registration",
    formCode: `DOC-V${form.versionNumber}`,
    estimatedMinutes: 4,
    fieldCount: 6,
    hasSignatureBox: true,
    previewSections: [
      {
        heading: "1. Applicant Details",
        sectionTitle: "Applicant Details",
        fields: ["Full Name", "Date of Birth", "Address"],
      },
      {
        heading: "2. Form Details",
        sectionTitle: "Form Details",
        fields: ["Declaration & Confirmation"],
      },
    ],
  };
}
