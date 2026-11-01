export interface Organization {
  id: string;
  name: string;
  slug: string;
  billing_plan: string;
  allowed_cases_per_month: number;
  role: string;
  created_at: string;
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
