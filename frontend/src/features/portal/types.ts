export interface Organization {
  id: string;
  name: string;
  slug: string;
  billing_plan: string;
  allowed_cases_per_month: number;
  role: string;
  organization_type?: "government" | "business";
  verification_status: string;
  is_verified_government: boolean;
  verification_details?: Record<string, unknown> | null;
  description?: string | null;
  logo_storage_path?: string | null;
  cover_image_storage_path?: string | null;
  office_address?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  official_website_url?: string | null;
  supported_languages: string[];
  created_at: string;
}

export interface OrganizationMember {
  id: string;
  user_id: string;
  email: string;
  role: string;
  created_at: string;
}

export interface OrganizationProfileUpdatePayload {
  name?: string;
  description?: string;
  office_address?: string;
  contact_email?: string;
  contact_phone?: string;
  official_website_url?: string;
  supported_languages?: string[];
}

export interface OrganizationVerificationPayload {
  authority_name: string;
  registration_id: string;
  official_domain: string;
  contact_person_title: string;
  notes?: string;
}

export type CaseStatus = "invited" | "in_progress" | "awaiting_review" | "completed";

export interface Case {
  id: string;
  public_id: string;
  organization_id: string;
  candidate_name: string;
  candidate_email: string;
  status: CaseStatus;
  form_version_id: string;
  form_title?: string | null;
  form_session_id?: string | null;
  session_public_id?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  invite_token?: string | null;
  total_fields: number;
  answered_fields: number;
  progress_percent: number;
}

export interface CaseCreatePayload {
  candidate_name: string;
  candidate_email: string;
  form_version_id: string;
  user_language?: string;
  notes?: string;
}

export interface CaseUpdatePayload {
  status?: CaseStatus;
  notes?: string;
}

export interface CandidateIntakeInfo {
  session_id: string;
  session_token: string;
  case_public_id: string;
  candidate_name: string;
  candidate_email: string;
  form_title: string;
  form_version_id: string;
  user_language: string;
  source_language: string;
  status: string;
}

export interface PublishedFormSummary {
  id: string;
  title: string;
  key?: string;
  description?: string;
  supported_languages?: string[];
}

export interface SubscriptionInfo {
  id: string;
  organization_id: string;
  plan_key: string;
  status: string;
  monthly_case_limit: number;
  cases_used_this_period: number;
  remaining_cases: number;
  current_period_start?: string | null;
  current_period_end?: string | null;
  cancel_at_period_end: boolean;
}

export interface PlanInfo {
  plan_key: string;
  name: string;
  monthly_cases: number;
  price_eur: number;
  is_paid: boolean;
  features: string[];
}
