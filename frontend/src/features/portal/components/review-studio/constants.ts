export const FIELD_TYPE_OPTIONS = [
  { value: "string", label: "Text / String" },
  { value: "date", label: "Date (ISO 8601)" },
  { value: "choice", label: "Choice / Dropdown / Radio" },
  { value: "number", label: "Number / Currency" },
  { value: "boolean", label: "Checkbox / Boolean" },
  { value: "signature", label: "Signature / Biometric Pad" },
];

export const CANONICAL_VAULT_KEYS = [
  { key: "personal.first_name", label: "First Name (personal.first_name)" },
  { key: "personal.last_name", label: "Last Name (personal.last_name)" },
  { key: "personal.date_of_birth", label: "Date of Birth (personal.date_of_birth)" },
  { key: "personal.place_of_birth", label: "Place of Birth (personal.place_of_birth)" },
  { key: "personal.nationality", label: "Nationality (personal.nationality)" },
  { key: "contact.email", label: "Email Address (contact.email)" },
  { key: "contact.phone", label: "Phone Number (contact.phone)" },
  { key: "residence.street_and_number", label: "Street & Number / Anschrift (residence.street_and_number)" },
  { key: "residence.postal_code", label: "Postal Code (residence.postal_code)" },
  { key: "residence.city", label: "City (residence.city)" },
  { key: "residence.country", label: "Country (residence.country)" },
  { key: "financial.iban", label: "IBAN (financial.iban)" },
  { key: "residence.move_in_date", label: "Move-in Date (residence.move_in_date)" },
  { key: "signature.applicant", label: "Applicant Signature (signature.applicant)" },
];
