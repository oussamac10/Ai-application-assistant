"use client";

import React, { useEffect, useState } from "react";
import {
  Building2,
  ShieldCheck,
  Users,
  Upload,
  CheckCircle2,
  AlertCircle,
  Clock,
  Trash2,
  Mail,
  UserPlus,
  Save,
  Globe,
  Building,
  Phone,
  MapPin,
  ExternalLink,
  X,
  Palette,
  Sliders,
  Eye,
  ArrowUp,
  ArrowDown,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import {
  LanguageSelectionModal,
  LANGUAGE_MAP,
} from "./LanguageSelectionModal";
import {
  Organization,
  OrganizationMember,
  OrganizationProfileUpdatePayload,
  OrganizationVerificationPayload,
  UIThemeConfig,
  SidebarTheme,
  LayoutDensity,
  SectionKey,
} from "../types";
import {
  DEFAULT_THEME_CONFIG,
  POPULAR_AUTHORITY_PALETTES,
  resolveThemeConfig,
  getContrastTextColor,
} from "../utils/theme";
import {
  getCurrentOrganization,
  inviteOrganizationMember,
  listOrganizationMembers,
  removeMember,
  submitOrganizationVerification,
  updateMemberRole,
  updateOrganizationProfile,
  uploadOrganizationLogo,
} from "../services/portalClient";
import { useOrganization } from "../context/OrganizationContext";

interface Props {
  initialOrg: Organization;
  onOrgUpdated: (updated: Organization) => void;
}

export function OrganizationSettings({ initialOrg, onOrgUpdated }: Props) {
  const { refreshOrganization } = useOrganization();
  const [activeTab, setActiveTab] = useState<"profile" | "verification" | "team" | "layout">("profile");
  const [org, setOrg] = useState<Organization>(initialOrg);
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);

  // Layout & Theme state
  const [themeConfig, setThemeConfig] = useState<UIThemeConfig>(() =>
    resolveThemeConfig(initialOrg.ui_theme_config)
  );
  const [savingTheme, setSavingTheme] = useState(false);
  const [themeSuccessMsg, setThemeSuccessMsg] = useState<string | null>(null);

  // Profile Form state
  const [name, setName] = useState(initialOrg.name);
  const [description, setDescription] = useState(initialOrg.description || "");
  const [officeAddress, setOfficeAddress] = useState(initialOrg.office_address || "");
  const [contactEmail, setContactEmail] = useState(initialOrg.contact_email || "");
  const [contactPhone, setContactPhone] = useState(initialOrg.contact_phone || "");
  const [websiteUrl, setWebsiteUrl] = useState(initialOrg.official_website_url || "");
  const [supportedLanguages, setSupportedLanguages] = useState<string[]>(
    initialOrg.supported_languages || ["de", "en"]
  );
  const [isLanguageModalOpen, setIsLanguageModalOpen] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileSuccessMsg, setProfileSuccessMsg] = useState<string | null>(null);

  // Logo upload state
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [logoVersion, setLogoVersion] = useState(Date.now());

  // Verification Form state
  const [authorityName, setAuthorityName] = useState(initialOrg.name);
  const [registrationId, setRegistrationId] = useState("");
  const [officialDomain, setOfficialDomain] = useState("");
  const [contactPersonTitle, setContactPersonTitle] = useState("");
  const [verificationNotes, setVerificationNotes] = useState("");
  const [submittingVerif, setSubmittingVerif] = useState(false);

  // Member invitation state
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("case_manager");
  const [inviting, setInviting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isOwnerOrAdmin = org.role === "owner" || org.role === "admin";

  const fetchMembers = async () => {
    setLoadingMembers(true);
    try {
      const data = await listOrganizationMembers();
      setMembers(data);
    } catch (err: unknown) {
      console.error("Failed to load members:", err);
    } finally {
      setLoadingMembers(false);
    }
  };

  useEffect(() => {
    if (activeTab === "team") {
      fetchMembers();
    }
  }, [activeTab]);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isOwnerOrAdmin) return;
    setSavingProfile(true);
    setErrorMsg(null);
    setProfileSuccessMsg(null);

    const payload: OrganizationProfileUpdatePayload = {
      name,
      description: description || undefined,
      office_address: officeAddress || undefined,
      contact_email: contactEmail || undefined,
      contact_phone: contactPhone || undefined,
      official_website_url: websiteUrl || undefined,
      supported_languages: supportedLanguages,
    };

    try {
      const updated = await updateOrganizationProfile(payload);
      setOrg(updated);
      onOrgUpdated(updated);
      refreshOrganization();
      setProfileSuccessMsg("Workspace profile successfully saved.");
      setTimeout(() => setProfileSuccessMsg(null), 4000);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to update profile.");
    } finally {
      setSavingProfile(false);
    }
  };

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !isOwnerOrAdmin) return;
    setUploadingLogo(true);
    setErrorMsg(null);
    try {
      const updated = await uploadOrganizationLogo(file);
      setOrg(updated);
      onOrgUpdated(updated);
      refreshOrganization();
      setLogoVersion(Date.now());
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to upload logo.");
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleSubmitVerification = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isOwnerOrAdmin) return;
    setSubmittingVerif(true);
    setErrorMsg(null);

    const payload: OrganizationVerificationPayload = {
      authority_name: authorityName,
      registration_id: registrationId,
      official_domain: officialDomain,
      contact_person_title: contactPersonTitle,
      notes: verificationNotes || undefined,
    };

    try {
      const updated = await submitOrganizationVerification(payload);
      setOrg(updated);
      onOrgUpdated(updated);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Verification request failed.");
    } finally {
      setSubmittingVerif(false);
    }
  };

  const handleInviteMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim() || !isOwnerOrAdmin) return;
    setInviting(true);
    setErrorMsg(null);
    try {
      const newMember = await inviteOrganizationMember(inviteEmail.trim(), inviteRole);
      setMembers((prev) => [...prev, newMember]);
      setIsInviteModalOpen(false);
      setInviteEmail("");
      setInviteRole("case_manager");
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to invite member.");
    } finally {
      setInviting(false);
    }
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    if (!isOwnerOrAdmin) return;
    try {
      const updated = await updateMemberRole(userId, newRole);
      setMembers((prev) => prev.map((m) => (m.user_id === userId ? updated : m)));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to update role.");
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!isOwnerOrAdmin) return;
    if (!confirm("Are you sure you want to remove this member from your workspace?")) return;
    try {
      await removeMember(userId);
      setMembers((prev) => prev.filter((m) => m.user_id !== userId));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to remove member.");
    }
  };

  const toggleLanguage = (code: string) => {
    if (supportedLanguages.includes(code)) {
      if (supportedLanguages.length > 1) {
        setSupportedLanguages(supportedLanguages.filter((l) => l !== code));
      }
    } else {
      setSupportedLanguages([...supportedLanguages, code]);
    }
  };

  const handleSaveTheme = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isOwnerOrAdmin) return;
    setSavingTheme(true);
    setErrorMsg(null);
    setThemeSuccessMsg(null);
    try {
      const updated = await updateOrganizationProfile({
        ui_theme_config: themeConfig,
      });
      setOrg(updated);
      onOrgUpdated(updated);
      refreshOrganization();
      setThemeSuccessMsg("Layout & Appearance settings saved successfully.");
      setTimeout(() => setThemeSuccessMsg(null), 4000);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to update layout settings.");
    } finally {
      setSavingTheme(false);
    }
  };

  const moveSection = (index: number, direction: "up" | "down") => {
    const currentOrder = [...(themeConfig.section_order || DEFAULT_THEME_CONFIG.section_order)];
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= currentOrder.length) return;
    const temp = currentOrder[index];
    currentOrder[index] = currentOrder[targetIndex];
    currentOrder[targetIndex] = temp;
    setThemeConfig((prev) => ({ ...prev, section_order: currentOrder }));
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
      {/* Settings Navigation Tabs */}
      <div className="flex border-b border-slate-200 bg-slate-50/70 px-6 pt-3 gap-6">
        <button
          onClick={() => setActiveTab("profile")}
          className={`pb-3 text-xs font-bold inline-flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "profile"
              ? "border-indigo-600 text-indigo-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Building2 className="w-4 h-4" />
          Workspace & Branding
        </button>
        <button
          onClick={() => setActiveTab("verification")}
          className={`pb-3 text-xs font-bold inline-flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "verification"
              ? "border-indigo-600 text-indigo-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          Official Verification
          {org.is_verified_government ? (
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
          ) : org.verification_status === "pending_review" ? (
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
          ) : null}
        </button>
        <button
          onClick={() => setActiveTab("team")}
          className={`pb-3 text-xs font-bold inline-flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "team"
              ? "border-indigo-600 text-indigo-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Users className="w-4 h-4" />
          Team & Roles
        </button>
        <button
          onClick={() => setActiveTab("layout")}
          className={`pb-3 text-xs font-bold inline-flex items-center gap-2 border-b-2 transition-all ${
            activeTab === "layout"
              ? "border-indigo-600 text-indigo-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          <Palette className="w-4 h-4" />
          Layout & Appearance
        </button>
      </div>

      <div className="p-6 sm:p-8">
        {errorMsg && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-center gap-3 text-xs text-rose-800">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {profileSuccessMsg && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-3 text-xs text-emerald-800">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{profileSuccessMsg}</span>
          </div>
        )}

        {themeSuccessMsg && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-3 text-xs text-emerald-800">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{themeSuccessMsg}</span>
          </div>
        )}

        {/* TAB 1: Profile & Branding */}
        {activeTab === "profile" && (
          <form onSubmit={handleSaveProfile} className="space-y-8 max-w-3xl">
            {/* Logo & Header Info */}
            <div className="flex flex-col sm:flex-row items-start gap-6 pb-6 border-b border-slate-100">
              <div className="relative group shrink-0">
                <div className="w-24 h-24 rounded-2xl border-2 border-slate-200 bg-white flex flex-col items-center justify-center overflow-hidden shadow-2xs p-1.5">
                  {org.logo_storage_path ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={`/api/organizations/${org.id}/logo?v=${logoVersion}`}
                      alt={`${org.name} logo`}
                      className="w-full h-full object-contain"
                    />
                  ) : (
                    <div className="w-full h-full rounded-xl bg-slate-50 flex flex-col items-center justify-center text-slate-400">
                      <Building className="w-8 h-8 text-slate-400" />
                      <span className="text-[10px] font-semibold mt-1">No Logo</span>
                    </div>
                  )}
                </div>
                {isOwnerOrAdmin && (
                  <label className="mt-2 block text-center cursor-pointer">
                    <span className="text-[11px] font-bold text-indigo-600 hover:text-indigo-800 transition-colors">
                      {uploadingLogo ? "Uploading..." : "Upload Logo (SVG / PNG)"}
                    </span>
                    <input
                      type="file"
                      accept=".svg,.png,.jpg,.jpeg,.webp,image/svg+xml,image/png,image/jpeg,image/webp"
                      onChange={handleLogoUpload}
                      disabled={uploadingLogo}
                      className="hidden"
                    />
                  </label>
                )}
              </div>

              <div className="space-y-1.5 flex-1 text-start">
                <h3 className="text-base font-bold text-slate-900">{org.name}</h3>
                <p className="text-xs text-slate-500 font-mono">
                  Slug: <span className="text-indigo-600">/organizations/{org.slug}</span>
                </p>
                <p className="text-xs text-slate-500">
                  This official identity and logo will appear on your public citizen portal, printable QR counter posters, and PDF instructions.
                </p>
              </div>
            </div>

            {/* Editable Fields */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 text-start">
              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-xs font-bold text-slate-800">
                  Official Organization Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={!isOwnerOrAdmin}
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-xs focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  required
                />
              </div>

              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-xs font-bold text-slate-800">
                  Description / Citizen Guidance
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={!isOwnerOrAdmin}
                  rows={3}
                  placeholder="e.g. Municipal migration and residence authority for administrative districts."
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-xs focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-800">Office Address</label>
                <div className="relative">
                  <MapPin className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="text"
                    value={officeAddress}
                    onChange={(e) => setOfficeAddress(e.target.value)}
                    disabled={!isOwnerOrAdmin}
                    placeholder="e.g. 100 City Hall Plaza, Suite 400"
                    className="w-full rounded-xl border border-slate-300 pl-9 pr-3.5 py-2.5 text-xs focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-800">Official Website</label>
                <div className="relative">
                  <Globe className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="url"
                    value={websiteUrl}
                    onChange={(e) => setWebsiteUrl(e.target.value)}
                    disabled={!isOwnerOrAdmin}
                    placeholder="https://www.citygov.example.org"
                    className="w-full rounded-xl border border-slate-300 pl-9 pr-3.5 py-2.5 text-xs focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-800">Official Contact Email</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    disabled={!isOwnerOrAdmin}
                    placeholder="citizenservices@citygov.example.org"
                    className="w-full rounded-xl border border-slate-300 pl-9 pr-3.5 py-2.5 text-xs focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-800">Contact Phone</label>
                <div className="relative">
                  <Phone className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="tel"
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    disabled={!isOwnerOrAdmin}
                    placeholder="+49 711 216 0"
                    className="w-full rounded-xl border border-slate-300 pl-9 pr-3.5 py-2.5 text-xs focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>
              </div>
            </div>

            {/* Supported Guidance Languages */}
            <div className="space-y-3 text-start pt-2">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div>
                  <label className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <Globe className="w-4 h-4 text-indigo-600" />
                    Supported Guidance Languages for Citizens
                  </label>
                  <p className="text-[11px] text-slate-500">
                    Citizens can choose any of these languages to guide them through your official forms with plain-language explanations.
                  </p>
                </div>
                {isOwnerOrAdmin && (
                  <button
                    type="button"
                    onClick={() => setIsLanguageModalOpen(true)}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-indigo-200 bg-indigo-50/80 px-3.5 py-1.5 text-xs font-bold text-indigo-700 hover:bg-indigo-100 transition-colors self-start sm:self-auto shadow-2xs"
                  >
                    <Globe className="w-3.5 h-3.5" />
                    Manage Languages ({supportedLanguages.length})
                  </button>
                )}
              </div>

              {/* Selected Language Chips */}
              <div className="flex flex-wrap gap-2 pt-1">
                {supportedLanguages.map((code) => {
                  const info = LANGUAGE_MAP.get(code);
                  const nativeName = info?.native || code;
                  const englishName = info?.name || "";

                  return (
                    <span
                      key={code}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50/90 px-3 py-1.5 text-xs font-semibold text-slate-800 shadow-2xs"
                    >
                      <span className="font-bold">{nativeName}</span>
                      {englishName && englishName !== nativeName && (
                        <span className="text-[10px] text-slate-400 font-normal">
                          ({englishName})
                        </span>
                      )}
                      <span className="font-mono text-[9px] font-bold uppercase text-indigo-600 bg-indigo-50 px-1 py-0.2 rounded">
                        {code}
                      </span>
                      {isOwnerOrAdmin && supportedLanguages.length > 1 && (
                        <button
                          type="button"
                          onClick={() => toggleLanguage(code)}
                          title={`Remove ${nativeName}`}
                          className="ms-0.5 rounded-full p-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 transition-colors"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </span>
                  );
                })}
              </div>
            </div>

            {isOwnerOrAdmin && (
              <div className="pt-4 flex justify-end">
                <button
                  type="submit"
                  disabled={savingProfile}
                  className="btn-primary py-2.5 px-5 text-xs font-bold inline-flex items-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  {savingProfile ? "Saving Changes..." : "Save Workspace Profile"}
                </button>
              </div>
            )}
          </form>
        )}

        {/* TAB 2: Official Government Verification */}
        {activeTab === "verification" && (
          <div className="space-y-6 max-w-2xl text-start">
            <div className="p-5 rounded-2xl border bg-slate-50 flex items-start gap-4">
              <div className="p-3 rounded-xl bg-white border border-slate-200 shadow-xs shrink-0">
                {org.is_verified_government ? (
                  <ShieldCheck className="w-6 h-6 text-emerald-600" />
                ) : org.verification_status === "pending_review" ? (
                  <Clock className="w-6 h-6 text-amber-600" />
                ) : (
                  <AlertCircle className="w-6 h-6 text-slate-400" />
                )}
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-bold text-slate-900">
                    {org.is_verified_government
                      ? "Verified Government Authority"
                      : org.verification_status === "pending_review"
                      ? "Verification Under Official Review"
                      : "Unverified Organization"}
                  </h4>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                      org.is_verified_government
                        ? "bg-emerald-100 text-emerald-800"
                        : org.verification_status === "pending_review"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-slate-200 text-slate-700"
                    }`}
                  >
                    {org.verification_status}
                  </span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {org.is_verified_government
                    ? "Your organization is verified as an official municipality or public administration entity. The verified badge is displayed on your public citizen portal and form links."
                    : org.verification_status === "pending_review"
                    ? "Your verification request has been submitted to platform administrators. We cross-reference municipal registries and domain authorization before issuing the verified government badge."
                    : "To display the official government badge on your portal and printable citizen counter signs, submit your municipal or institutional registration details below."}
                </p>
              </div>
            </div>

            {!org.is_verified_government && (
              <form onSubmit={handleSubmitVerification} className="space-y-4 pt-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Official Verification Application
                </h3>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-800">
                    Authority / Institution Name
                  </label>
                  <input
                    type="text"
                    value={authorityName}
                    onChange={(e) => setAuthorityName(e.target.value)}
                    required
                    className="w-full rounded-xl border border-slate-300 px-3.5 py-2 text-xs focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-800">
                    Official Registration / Service ID
                  </label>
                  <input
                    type="text"
                    value={registrationId}
                    onChange={(e) => setRegistrationId(e.target.value)}
                    placeholder="e.g. DE-BW-08111000 or Municipal Code"
                    required
                    className="w-full rounded-xl border border-slate-300 px-3.5 py-2 text-xs focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-800">
                    Official Government / Institutional Domain
                  </label>
                  <input
                    type="text"
                    value={officialDomain}
                    onChange={(e) => setOfficialDomain(e.target.value)}
                    placeholder="e.g. agency.gov or city.gov"
                    required
                    className="w-full rounded-xl border border-slate-300 px-3.5 py-2 text-xs focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-800">
                    Submitter Role / Title
                  </label>
                  <input
                    type="text"
                    value={contactPersonTitle}
                    onChange={(e) => setContactPersonTitle(e.target.value)}
                    placeholder="e.g. Amtsleiter / Department Head"
                    required
                    className="w-full rounded-xl border border-slate-300 px-3.5 py-2 text-xs focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-800">
                    Additional Notes (Optional)
                  </label>
                  <textarea
                    value={verificationNotes}
                    onChange={(e) => setVerificationNotes(e.target.value)}
                    rows={2}
                    placeholder="Provide any public register links or verification documents..."
                    className="w-full rounded-xl border border-slate-300 px-3.5 py-2 text-xs focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={submittingVerif || org.verification_status === "pending_review"}
                  className="btn-primary py-2.5 px-4 text-xs font-bold inline-flex items-center gap-2"
                >
                  <ShieldCheck className="w-4 h-4" />
                  {submittingVerif
                    ? "Submitting..."
                    : org.verification_status === "pending_review"
                    ? "Update Verification Request"
                    : "Submit for Official Verification"}
                </button>
              </form>
            )}
          </div>
        )}

        {/* TAB 3: Team & Roles */}
        {activeTab === "team" && (
          <div className="space-y-6 text-start">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-slate-900">Workspace Staff & Roles</h3>
                  <span className="rounded-full bg-indigo-50 border border-indigo-200 px-2.5 py-0.5 text-xs font-bold text-indigo-700">
                    {members.length} {members.length === 1 ? "Member" : "Members"}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Assign administrative, form editor, or case management permissions to your team.
                </p>
              </div>

              {isOwnerOrAdmin && (
                <button
                  type="button"
                  onClick={() => setIsInviteModalOpen(true)}
                  className="btn-primary py-2 px-4 text-xs font-bold inline-flex items-center gap-2 shadow-xs"
                >
                  <UserPlus className="w-4 h-4" />
                  Invite Colleague
                </button>
              )}
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-2xl bg-white shadow-2xs">
              <table className="w-full text-xs text-start">
                <thead className="bg-slate-50/80 text-slate-600 font-bold border-b border-slate-200 uppercase tracking-wider text-[11px]">
                  <tr>
                    <th scope="col" className="py-3.5 px-5 text-start w-5/12">Member</th>
                    <th scope="col" className="py-3.5 px-5 text-start w-3/12">Assigned Role</th>
                    <th scope="col" className="py-3.5 px-5 text-start w-2/12">Joined Date</th>
                    {isOwnerOrAdmin && (
                      <th scope="col" className="py-3.5 px-5 text-end w-2/12">Actions</th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {members.map((m) => (
                    <tr key={m.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-4 px-5">
                        <div className="flex items-center gap-3">
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-indigo-50 to-indigo-100 border border-indigo-200 font-mono text-xs font-bold text-indigo-700">
                            {m.email.charAt(0).toUpperCase()}
                          </span>
                          <div>
                            <div className="font-semibold text-slate-900">{m.email}</div>
                            {m.role === "owner" && (
                              <span className="text-[10px] font-semibold text-indigo-600">
                                Workspace Creator
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-5">
                        {isOwnerOrAdmin && m.role !== "owner" ? (
                          <select
                            value={m.role}
                            onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                            className="bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-700 shadow-2xs focus:border-indigo-600 focus:outline-none focus:ring-1 focus:ring-indigo-600"
                          >
                            <option value="admin">Administrator</option>
                            <option value="form_editor">Form Editor</option>
                            <option value="case_manager">Case Manager</option>
                            <option value="viewer">Viewer (Read-only)</option>
                          </select>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 border border-indigo-200 px-3 py-1 text-xs font-bold text-indigo-700">
                            <span className="h-1.5 w-1.5 rounded-full bg-indigo-600" />
                            Owner
                          </span>
                        )}
                      </td>
                      <td className="py-4 px-5 text-slate-500 font-mono text-[11px]">
                        {new Date(m.created_at).toLocaleDateString(undefined, {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                        })}
                      </td>
                      {isOwnerOrAdmin && (
                        <td className="py-4 px-5 text-end">
                          {m.role !== "owner" ? (
                            <button
                              type="button"
                              onClick={() => handleRemoveMember(m.user_id)}
                              className="inline-flex items-center gap-1 text-xs text-rose-600 hover:text-rose-800 hover:bg-rose-50 px-2.5 py-1 rounded-lg transition-colors font-medium"
                              title="Remove member from workspace"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              <span>Remove</span>
                            </button>
                          ) : (
                            <span className="text-[11px] font-medium text-slate-400 italic">
                              Primary Owner
                            </span>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                  {members.length === 0 && !loadingMembers && (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-slate-400">
                        No team members registered.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 4: Layout & Appearance Customizer */}
        {activeTab === "layout" && (
          <form onSubmit={handleSaveTheme} className="space-y-8 max-w-4xl text-start">
            <div>
              <div className="flex items-center gap-2">
                <Palette className="w-5 h-5 text-indigo-600" />
                <h3 className="text-base font-bold text-slate-900">
                  System View, Colors & Component Layout
                </h3>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Customize your municipal authority workspace, heraldic brand colors, component ordering, and public portal appearance.
              </p>
            </div>

            {/* 1. Official Authority Brand Colors & Palettes */}
            <div className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-slate-900">Authority Brand Colors</h4>
                  <p className="text-xs text-slate-500">
                    Choose your official municipal heraldic color or select from official German authority palettes.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setThemeConfig((prev) => ({
                      ...prev,
                      primary_color: DEFAULT_THEME_CONFIG.primary_color,
                      accent_color: DEFAULT_THEME_CONFIG.accent_color,
                    }))
                  }
                  className="inline-flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-800 font-semibold"
                >
                  <RotateCcw className="w-3 h-3" /> Reset Colors
                </button>
              </div>

              {/* Popular Swatches */}
              <div className="space-y-2">
                <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                  Preset Authority Palettes:
                </span>
                <div className="flex flex-wrap gap-2">
                  {POPULAR_AUTHORITY_PALETTES.map((p) => {
                    const isSelected =
                      themeConfig.primary_color?.toLowerCase() === p.primary.toLowerCase();
                    return (
                      <button
                        key={p.name}
                        type="button"
                        onClick={() =>
                          setThemeConfig((prev) => ({
                            ...prev,
                            primary_color: p.primary,
                            accent_color: p.accent,
                          }))
                        }
                        className={`inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-semibold border transition-all ${
                          isSelected
                            ? "border-slate-900 bg-white ring-2 ring-slate-900 shadow-xs"
                            : "border-slate-200 bg-white hover:border-slate-300 text-slate-700"
                        }`}
                      >
                        <span
                          className="w-3.5 h-3.5 rounded-full border border-black/10 shrink-0"
                          style={{ backgroundColor: p.primary }}
                        />
                        <span>{p.name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Custom Hex Inputs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-800">Primary Brand Color (Buttons & Highlights)</label>
                  <div className="flex items-center gap-2.5">
                    <input
                      type="color"
                      value={themeConfig.primary_color || "#4f46e5"}
                      onChange={(e) =>
                        setThemeConfig((prev) => ({ ...prev, primary_color: e.target.value }))
                      }
                      className="h-9 w-9 rounded-xl border border-slate-300 cursor-pointer p-0.5 bg-white"
                    />
                    <input
                      type="text"
                      value={themeConfig.primary_color || ""}
                      onChange={(e) =>
                        setThemeConfig((prev) => ({ ...prev, primary_color: e.target.value }))
                      }
                      placeholder="#FEDB00"
                      className="font-mono text-xs uppercase flex-1 rounded-xl border border-slate-300 px-3 py-2 bg-white"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-800">Accent / Secondary Color</label>
                  <div className="flex items-center gap-2.5">
                    <input
                      type="color"
                      value={themeConfig.accent_color || "#6366f1"}
                      onChange={(e) =>
                        setThemeConfig((prev) => ({ ...prev, accent_color: e.target.value }))
                      }
                      className="h-9 w-9 rounded-xl border border-slate-300 cursor-pointer p-0.5 bg-white"
                    />
                    <input
                      type="text"
                      value={themeConfig.accent_color || ""}
                      onChange={(e) =>
                        setThemeConfig((prev) => ({ ...prev, accent_color: e.target.value }))
                      }
                      placeholder="#3B82F6"
                      className="font-mono text-xs uppercase flex-1 rounded-xl border border-slate-300 px-3 py-2 bg-white"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* 2. Sidebar & Navigation Appearance */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4">
              <div>
                <h4 className="text-sm font-bold text-slate-900">Sidebar Theme</h4>
                <p className="text-xs text-slate-500">
                  Select the visual appearance of the left administrative navigation menu.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  {
                    id: "dark" as SidebarTheme,
                    title: "Dark Authority",
                    desc: "Modern contrast dark slate background",
                    previewBg: "bg-[#0B0F19]",
                    previewText: "text-white",
                  },
                  {
                    id: "light" as SidebarTheme,
                    title: "Municipal Light",
                    desc: "Classic clean white government style",
                    previewBg: "bg-white border border-slate-200",
                    previewText: "text-slate-900",
                  },
                  {
                    id: "heraldic" as SidebarTheme,
                    title: "Heraldic Tint",
                    desc: "Deep tone tinted with authority brand color",
                    previewBg: "bg-[#0b1329]",
                    previewText: "text-amber-300",
                  },
                ].map((st) => {
                  const isSelected = (themeConfig.sidebar_theme || "dark") === st.id;
                  return (
                    <button
                      key={st.id}
                      type="button"
                      onClick={() =>
                        setThemeConfig((prev) => ({ ...prev, sidebar_theme: st.id }))
                      }
                      className={`p-4 rounded-2xl text-start border transition-all ${
                        isSelected
                          ? "border-indigo-600 ring-2 ring-indigo-600/30 bg-indigo-50/30"
                          : "border-slate-200 hover:border-slate-300 bg-white"
                      }`}
                    >
                      <div className={`h-8 w-full rounded-lg mb-2.5 flex items-center px-2.5 gap-1.5 ${st.previewBg}`}>
                        <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                        <span className={`text-[10px] font-bold ${st.previewText}`}>STUTTGART</span>
                      </div>
                      <div className="text-xs font-bold text-slate-900">{st.title}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5">{st.desc}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 3. Component Ordering on Dashboard */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4">
              <div>
                <h4 className="text-sm font-bold text-slate-900">Dashboard Component Ordering</h4>
                <p className="text-xs text-slate-500">
                  Control the visual order in which sections appear on the main Forms & Review Studio portal.
                </p>
              </div>

              <div className="space-y-2">
                {(themeConfig.section_order || DEFAULT_THEME_CONFIG.section_order).map((sec, idx, arr) => {
                  const labelMap: Record<SectionKey, { name: string; desc: string }> = {
                    header: {
                      name: "Authority Header & Seal",
                      desc: "Official crest, authority name, verification badge, and contact metadata",
                    },
                    metrics: {
                      name: "Real-time Forms Metrics Strip",
                      desc: "Summary cards showing total forms, live forms, needs review, and archived",
                    },
                    actions: {
                      name: "Action Bar & PDF Ingestion",
                      desc: "Upload PDF button and Public Citizen Portal link",
                    },
                    forms: {
                      name: "Official Forms & Review Studio Catalog",
                      desc: "Full table of administrative templates with search, filters, and actions",
                    },
                  };

                  return (
                    <div
                      key={sec}
                      className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-slate-50/70"
                    >
                      <div className="flex items-center gap-3">
                        <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-white border border-slate-200 text-xs font-mono font-bold text-slate-700">
                          {idx + 1}
                        </span>
                        <div>
                          <div className="text-xs font-bold text-slate-900">{labelMap[sec]?.name}</div>
                          <div className="text-[11px] text-slate-500">{labelMap[sec]?.desc}</div>
                        </div>
                      </div>

                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => moveSection(idx, "up")}
                          disabled={idx === 0}
                          className="p-1 rounded-lg border border-slate-200 bg-white text-slate-600 hover:text-slate-900 disabled:opacity-30 disabled:cursor-not-allowed"
                          title="Move up"
                        >
                          <ArrowUp className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => moveSection(idx, "down")}
                          disabled={idx === arr.length - 1}
                          className="p-1 rounded-lg border border-slate-200 bg-white text-slate-600 hover:text-slate-900 disabled:opacity-30 disabled:cursor-not-allowed"
                          title="Move down"
                        >
                          <ArrowDown className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 4. Component Visibility Toggles */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4">
              <div>
                <h4 className="text-sm font-bold text-slate-900">Component Visibility</h4>
                <p className="text-xs text-slate-500">
                  Toggle which elements are visible to your caseworkers and administrators.
                </p>
              </div>

              <div className="divide-y divide-slate-100">
                <div className="flex items-center justify-between py-3">
                  <div>
                    <div className="text-xs font-bold text-slate-900">Show Real-Time Metrics Strip</div>
                    <div className="text-[11px] text-slate-500">
                      Display total forms, published forms, and review count cards on dashboard.
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={themeConfig.show_metrics_strip !== false}
                    onChange={(e) =>
                      setThemeConfig((prev) => ({ ...prev, show_metrics_strip: e.target.checked }))
                    }
                    className="h-4 w-4 rounded text-indigo-600 focus:ring-indigo-500"
                  />
                </div>

                <div className="flex items-center justify-between py-3">
                  <div>
                    <div className="text-xs font-bold text-slate-900">Show Authority Contact & Location Details</div>
                    <div className="text-[11px] text-slate-500">
                      Display office address, phone, email, and website on header bar.
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={themeConfig.show_authority_metadata !== false}
                    onChange={(e) =>
                      setThemeConfig((prev) => ({
                        ...prev,
                        show_authority_metadata: e.target.checked,
                      }))
                    }
                    className="h-4 w-4 rounded text-indigo-600 focus:ring-indigo-500"
                  />
                </div>

                <div className="flex items-center justify-between py-3">
                  <div>
                    <div className="text-xs font-bold text-slate-900">Show Public Citizen Portal Link</div>
                    <div className="text-[11px] text-slate-500">
                      Display the quick 1-click button to view public citizen intake.
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={themeConfig.show_portal_link !== false}
                    onChange={(e) =>
                      setThemeConfig((prev) => ({ ...prev, show_portal_link: e.target.checked }))
                    }
                    className="h-4 w-4 rounded text-indigo-600 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* 5. Density & Spacing */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4">
              <div>
                <h4 className="text-sm font-bold text-slate-900">Layout Density</h4>
                <p className="text-xs text-slate-500">
                  Select interface spacing for your team.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  {
                    id: "comfortable" as LayoutDensity,
                    title: "Comfortable (Standard)",
                    desc: "Spacious padding, large cards, and standard typography",
                  },
                  {
                    id: "compact" as LayoutDensity,
                    title: "Compact (High-Density)",
                    desc: "Tight padding and compact tables for high-throughput intake",
                  },
                ].map((d) => {
                  const isSelected = (themeConfig.layout_density || "comfortable") === d.id;
                  return (
                    <button
                      key={d.id}
                      type="button"
                      onClick={() => setThemeConfig((prev) => ({ ...prev, layout_density: d.id }))}
                      className={`p-3.5 rounded-xl text-start border transition-all ${
                        isSelected
                          ? "border-indigo-600 ring-2 ring-indigo-600/30 bg-indigo-50/30 font-bold"
                          : "border-slate-200 hover:border-slate-300 bg-white"
                      }`}
                    >
                      <div className="text-xs text-slate-900">{d.title}</div>
                      <div className="text-[11px] text-slate-500 font-normal mt-0.5">{d.desc}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 6. Public Citizen Portal Customization */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 space-y-4">
              <div>
                <h4 className="text-sm font-bold text-slate-900">Public Citizen Guidance & Notices</h4>
                <p className="text-xs text-slate-500">
                  Customize the headline and banner shown to applicants on your public portal (`/organizations/{org.slug}`).
                </p>
              </div>

              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-800">Citizen Welcome Headline</label>
                  <input
                    type="text"
                    value={themeConfig.citizen_welcome_heading || ""}
                    onChange={(e) =>
                      setThemeConfig((prev) => ({
                        ...prev,
                        citizen_welcome_heading: e.target.value,
                      }))
                    }
                    placeholder="Herzlich willkommen beim Bürgeramt Stuttgart"
                    className="w-full rounded-xl border border-slate-300 px-3.5 py-2 text-xs bg-white focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-800">Public Notice Banner (Optional alert box)</label>
                  <input
                    type="text"
                    value={themeConfig.citizen_notice_banner || ""}
                    onChange={(e) =>
                      setThemeConfig((prev) => ({
                        ...prev,
                        citizen_notice_banner: e.target.value,
                      }))
                    }
                    placeholder="Öffnungszeiten: Montag–Freitag 08:00–16:00 Uhr. Barrierefreier Zugang."
                    className="w-full rounded-xl border border-slate-300 px-3.5 py-2 text-xs bg-white focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>
              </div>
            </div>

            {/* Live Interactive Preview Box */}
            <div className="rounded-2xl border-2 border-indigo-200 bg-linear-to-r from-indigo-50/50 via-white to-slate-50 p-6 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-600" />
                  <span className="text-xs font-bold text-slate-900">Live Appearance Preview</span>
                </div>
                <span className="text-[10px] font-mono font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                  THEME PREVIEW
                </span>
              </div>

              <div className="rounded-xl border border-slate-300 bg-white p-4 shadow-sm space-y-3">
                <div className="flex items-center justify-between border-b pb-3 border-slate-100">
                  <div className="flex items-center gap-2.5">
                    <div
                      className="w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs shadow-2xs"
                      style={{
                        backgroundColor: themeConfig.primary_color || "#4f46e5",
                        color: getContrastTextColor(themeConfig.primary_color || "#4f46e5"),
                      }}
                    >
                      🏛️
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-900">{org.name}</div>
                      <div className="text-[10px] text-slate-400">Verified Official Authority</div>
                    </div>
                  </div>
                  <button
                    type="button"
                    style={{
                      backgroundColor: themeConfig.primary_color || "#4f46e5",
                      color: getContrastTextColor(themeConfig.primary_color || "#4f46e5"),
                    }}
                    className="px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs cursor-default"
                  >
                    + Upload PDF
                  </button>
                </div>

                {themeConfig.show_metrics_strip !== false && (
                  <div className="grid grid-cols-4 gap-2 pt-1">
                    {["Total: 12", "Live: 8", "Review: 2", "Archived: 2"].map((m, i) => (
                      <div key={i} className="p-2 rounded-lg bg-slate-50 text-[10px] font-semibold text-slate-600 text-center border border-slate-100">
                        {m}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Save Button */}
            {isOwnerOrAdmin && (
              <div className="pt-2 flex justify-end">
                <button
                  type="submit"
                  disabled={savingTheme}
                  style={{
                    backgroundColor: themeConfig.primary_color || "#4f46e5",
                    color: getContrastTextColor(themeConfig.primary_color || "#4f46e5"),
                  }}
                  className="px-6 py-2.5 rounded-xl text-xs font-bold shadow-sm inline-flex items-center gap-2 hover:opacity-90 active:scale-[0.98] transition-all cursor-pointer"
                >
                  <Save className="w-4 h-4" />
                  <span>{savingTheme ? "Saving Settings..." : "Save Layout & Colors"}</span>
                </button>
              </div>
            )}
          </form>
        )}
      </div>

      {/* Invite Member Modal */}
      {isInviteModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 max-w-md w-full p-6 shadow-xl space-y-4 text-start">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">Invite Team Member</h3>
              <button
                onClick={() => setIsInviteModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleInviteMember} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-800">Colleague Email</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@amt.de"
                  required
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-xs focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-800">Role & Permissions</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-xs bg-white focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                >
                  <option value="case_manager">Case Manager (Manage cases & candidate links)</option>
                  <option value="form_editor">Form Editor (Upload & review form schemas)</option>
                  <option value="admin">Administrator (Manage workspace, staff & billing)</option>
                  <option value="viewer">Viewer (Read-only analytics & submissions)</option>
                </select>
              </div>

              <div className="pt-2 flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsInviteModalOpen(false)}
                  className="btn-secondary py-2 px-4 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inviting}
                  className="btn-primary py-2 px-4 text-xs font-bold inline-flex items-center gap-1.5"
                >
                  <UserPlus className="w-3.5 h-3.5" />
                  {inviting ? "Inviting..." : "Send Invitation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Language Selection Modal */}
      <LanguageSelectionModal
        isOpen={isLanguageModalOpen}
        onClose={() => setIsLanguageModalOpen(false)}
        selectedLanguages={supportedLanguages}
        onApply={(langs) => setSupportedLanguages(langs)}
      />
    </div>
  );
}
