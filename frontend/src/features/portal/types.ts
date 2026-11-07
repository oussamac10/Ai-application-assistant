export type SidebarTheme = "dark" | "light" | "heraldic";
export type LayoutDensity = "comfortable" | "compact";
export type SectionKey = "header" | "metrics" | "actions" | "forms";

export interface UIThemeConfig {
  primary_color?: string;
  accent_color?: string;
  sidebar_theme?: SidebarTheme;
  layout_density?: LayoutDensity;
  show_metrics_strip?: boolean;
  show_authority_metadata?: boolean;
  show_portal_link?: boolean;
  section_order?: SectionKey[];
  citizen_welcome_heading?: string | null;
  citizen_welcome_text?: string | null;
  citizen_notice_banner?: string | null;
}

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
  ui_theme_config?: UIThemeConfig | null;
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
  ui_theme_config?: UIThemeConfig | null;
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

export type FormLifecycleStatus = 'draft' | 'needs_review' | 'published' | 'archived';

export interface CategoryTranslation {
  name: string;
  description?: string | null;
}

export interface OrganizationCategory {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  icon?: string | null;
  description?: string | null;
  parent_id?: string | null;
  translations: Record<string, CategoryTranslation>;
  sort_order: number;
  is_active: boolean;
  forms_count: number;
  created_at: string;
  updated_at: string;
}

export interface OrganizationCategoryCreatePayload {
  name: string;
  slug?: string;
  icon?: string | null;
  description?: string | null;
  parent_id?: string | null;
  translations?: Record<string, CategoryTranslation>;
  sort_order?: number;
  is_active?: boolean;
}

export interface OrganizationCategoryUpdatePayload {
  name?: string;
  slug?: string;
  icon?: string | null;
  description?: string | null;
  parent_id?: string | null;
  translations?: Record<string, CategoryTranslation>;
  sort_order?: number;
  is_active?: boolean;
}

export interface PublicCategoryItem {
  id: string;
  name: string;
  slug: string;
  icon?: string | null;
  description?: string | null;
  parent_id?: string | null;
  translations: Record<string, CategoryTranslation>;
  sort_order: number;
  forms_count: number;
}

export interface OrganizationFormSummary {
  id: string;
  key: string;
  name: string;
  description?: string | null;
  category: string;
  category_id?: string | null;
  submissionMethod: string;
  instructions?: string | null;
  requiredDocuments: string[];
  activeVersionId?: string | null;
  versionNumber: number;
  status: FormLifecycleStatus;
  fieldsCount: number;
  sourcePdfStoragePath?: string | null;
  hasPdf: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface FormTranslationItem {
  language: string;
  label: string;
  helpText?: string | null;
  placeholder?: string | null;
}

export interface FormOptionItem {
  value: string;
  label: string;
  position: number;
}

export interface FormFieldItem {
  id: string;
  key: string;
  fieldType: string;
  required: boolean;
  requiredness: string;
  position: number;
  configuration: Record<string, unknown>;
  questionKey?: string | null;
  translations: FormTranslationItem[];
  options: FormOptionItem[];
}

export interface FormReviewDetail {
  templateId: string;
  versionId: string;
  key: string;
  name: string;
  description?: string | null;
  category: string;
  category_id?: string | null;
  submissionMethod: string;
  instructions?: string | null;
  requiredDocuments: string[];
  status: FormLifecycleStatus;
  versionNumber: number;
  sourceLanguage: string;
  sourcePdfStoragePath?: string | null;
  reviewNotes?: string | null;
  pageCount?: number;
  pageDimensions?: Array<{ page: number; width: number; height: number }>;
  fields: FormFieldItem[];
}

export interface FormReviewUpdatePayload {
  name?: string;
  description?: string;
  category?: string;
  category_id?: string | null;
  submissionMethod?: string;
  instructions?: string;
  requiredDocuments?: string[];
  reviewNotes?: string;
}

export interface PublicPublishedFormItem {
  id: string;
  key: string;
  name: string;
  description?: string | null;
  category: string;
  category_id?: string | null;
  category_slug?: string | null;
  category_name?: string | null;
  submission_method: string;
  instructions?: string | null;
  required_documents: string[];
  active_version_id: string;
  version_number: number;
  source_language: string;
  supported_output_languages: string[];
  fields_count: number;
  has_pdf: boolean;
}

export interface PublicOrganizationSummary {
  id: string;
  name: string;
  slug: string;
  organization_type: string;
  verification_status: string;
  is_verified_government: boolean;
  description?: string | null;
  office_address?: string | null;
  official_website_url?: string | null;
  has_logo: boolean;
  published_forms_count: number;
  supported_languages: string[];
}

export interface PublicOrganizationDetail extends PublicOrganizationSummary {
  contact_email?: string | null;
  contact_phone?: string | null;
  cover_image_storage_path?: string | null;
  ui_theme_config?: UIThemeConfig | null;
  categories?: PublicCategoryItem[];
  published_forms: PublicPublishedFormItem[];
}

export interface PublicFormDetail {
  id: string;
  key: string;
  name: string;
  description?: string | null;
  category: string;
  submission_method: string;
  instructions?: string | null;
  required_documents: string[];
  active_version_id: string;
  version_number: number;
  source_language: string;
  supported_output_languages: string[];
  fields_count: number;
  has_pdf: boolean;
  organization?: PublicOrganizationSummary | null;
  share_url: string;
  qr_svg_url: string;
  qr_png_url: string;
  counter_poster_pdf_url: string;
}



