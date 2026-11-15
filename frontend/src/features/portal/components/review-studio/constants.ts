export const FIELD_TYPE_OPTIONS = [
  { value: "string", label: "Short Text" },
  { value: "date", label: "Date" },
  { value: "choice", label: "Choice / Dropdown" },
  { value: "single_choice", label: "Single Choice" },
  { value: "multiple_choice", label: "Multiple Choice" },
  { value: "country", label: "Country / Nationality" },
  { value: "number", label: "Number / Amount" },
  { value: "boolean", label: "Yes / No Checkbox" },
  { value: "signature", label: "Signature" },
];

export const CANONICAL_VAULT_KEYS = [
  { key: "personal.first_name", label: "First Name" },
  { key: "personal.last_name", label: "Last Name" },
  { key: "personal.date_of_birth", label: "Date of Birth" },
  { key: "personal.place_of_birth", label: "Place of Birth" },
  { key: "personal.nationality", label: "Nationality" },
  { key: "contact.email", label: "Email Address" },
  { key: "contact.phone", label: "Phone Number" },
  { key: "residence.street_and_number", label: "Street & House Number" },
  { key: "residence.postal_code", label: "Postal Code" },
  { key: "residence.city", label: "City" },
  { key: "residence.country", label: "Country" },
  { key: "financial.iban", label: "Bank Account (IBAN)" },
  { key: "residence.move_in_date", label: "Move-in Date" },
  { key: "signature.applicant", label: "Applicant Signature" },
];
