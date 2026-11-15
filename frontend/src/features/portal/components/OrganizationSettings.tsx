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
  Search,
  Lock,
  FileText,
  FolderTree,
} from "lucide-react";
import { OrganizationCategoryManager } from "./OrganizationCategoryManager";
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
  const [activeTab, setActiveTab] = useState<"profile" | "verification" | "team" | "layout" | "categories">("profile");
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
    <div className="bg-[#0F1522] rounded-2xl border border-white/10 text-slate-100 shadow-xs overflow-hidden">
      {/* Settings Navigation Tabs */}
      <div className="flex border-b border-white/10 bg-[#0A0E17]/70 px-6 pt-3 gap-6 overflow-x-auto">
        <button
          onClick={() => setActiveTab("profile")}
          className={`pb-3 text-xs font-bold inline-flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === "profile"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Building2 className="w-4 h-4" />
          Workspace & Branding
        </button>
        <button
          onClick={() => setActiveTab("verification")}
          className={`pb-3 text-xs font-bold inline-flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === "verification"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
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
          className={`pb-3 text-xs font-bold inline-flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === "team"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Users className="w-4 h-4" />
          Team & Roles
        </button>
        <button
          onClick={() => setActiveTab("layout")}
          className={`pb-3 text-xs font-bold inline-flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === "layout"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Palette className="w-4 h-4" />
          Layout & Appearance
        </button>
        <button
          onClick={() => setActiveTab("categories")}
          className={`pb-3 text-xs font-bold inline-flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
            activeTab === "categories"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <FolderTree className="w-4 h-4" />
          Form Categories
        </button>
      </div>

      <div className="p-6 sm:p-8">
        {errorMsg && (
          <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center gap-3 text-xs text-rose-200">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
        )}

        {profileSuccessMsg && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3 text-xs text-emerald-300">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{profileSuccessMsg}</span>
          </div>
        )}

        {themeSuccessMsg && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3 text-xs text-emerald-300">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{themeSuccessMsg}</span>
          </div>
        )}

        {/* TAB 1: Profile & Branding */}
        {activeTab === "profile" && (
          <form onSubmit={handleSaveProfile} className="space-y-8 max-w-3xl">
            {/* Logo & Header Info */}
            <div className="flex flex-col sm:flex-row items-start gap-6 pb-6 border-b border-white/[0.08]">
              <div className="relative group shrink-0">
                <div
                  className={`w-24 h-24 rounded-2xl border-2 flex flex-col items-center justify-center overflow-hidden shadow-2xs ${
                    org.logo_storage_path
                      ? "border-white/20 bg-white p-1"
                      : "border-white/10 bg-[#151D2E] p-1.5"
                  }`}
                >
                  {org.logo_storage_path ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={`/api/organizations/${org.id}/logo?v=${logoVersion}`}
                      alt={`${org.name} logo`}
                      className="w-full h-full object-contain"
                    />
                  ) : (
                    <div className="w-full h-full rounded-xl bg-[#151D2E] flex flex-col items-center justify-center text-slate-400">
                      <Building className="w-8 h-8 text-slate-500" />
                      <span className="text-[10px] font-semibold mt-1 text-slate-400">No Logo</span>
                    </div>
                  )}
                </div>
                {isOwnerOrAdmin && (
                  <label className="mt-2 block text-center cursor-pointer">
                    <span className="text-[11px] font-bold text-emerald-400 hover:text-emerald-300 transition-colors">
                      {uploadingLogo ? "Uploading..." : "Upload Logo"}
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

              <div className="space-y-1.5 flex-1 min-w-0 text-start">
                <h3 className="text-base font-bold text-white break-words">{org.name}</h3>
                <p className="text-xs text-slate-400 break-all">
                  Public Link: <span className="text-emerald-400 font-medium">/organizations/{org.slug}</span>
                </p>
                <p className="text-xs text-slate-400">
                  This official identity and logo will appear on your public citizen portal, printable QR counter posters, and PDF instructions.
                </p>
              </div>
            </div>

            {/* Editable Fields */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 text-start">
              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-xs font-bold text-slate-200">
                  Official Organization Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={!isOwnerOrAdmin}
                  className="w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none disabled:opacity-60"
                  required
                />
              </div>

              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-xs font-bold text-slate-200">
                  Description / Citizen Guidance
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={!isOwnerOrAdmin}
                  rows={3}
                  placeholder="e.g. Municipal migration and residence authority for administrative districts."
                  className="w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none disabled:opacity-60"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-200">Office Address</label>
                <div className="relative">
                  <MapPin className="w-4 h-4 text-slate-500 absolute start-3 top-3" />
                  <input
                    type="text"
                    value={officeAddress}
                    onChange={(e) => setOfficeAddress(e.target.value)}
                    disabled={!isOwnerOrAdmin}
                    placeholder="e.g. 100 City Hall Plaza, Suite 400"
                    className="w-full rounded-xl border border-white/10 bg-[#0A0E17] ps-9 pe-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none disabled:opacity-60"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-200">Official Website</label>
                <div className="relative">
                  <Globe className="w-4 h-4 text-slate-500 absolute start-3 top-3" />
                  <input
                    type="url"
                    value={websiteUrl}
                    onChange={(e) => setWebsiteUrl(e.target.value)}
                    disabled={!isOwnerOrAdmin}
                    placeholder="https://www.citygov.example.org"
                    className="w-full rounded-xl border border-white/10 bg-[#0A0E17] ps-9 pe-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none disabled:opacity-60"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-200">Official Contact Email</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-500 absolute start-3 top-3" />
                  <input
                    type="email"
                    value={contactEmail}
                    onChange={(e) => setContactEmail(e.target.value)}
                    disabled={!isOwnerOrAdmin}
                    placeholder="citizenservices@citygov.example.org"
                    className="w-full rounded-xl border border-white/10 bg-[#0A0E17] ps-9 pe-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none disabled:opacity-60"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-200">Contact Phone</label>
                <div className="relative">
                  <Phone className="w-4 h-4 text-slate-500 absolute start-3 top-3" />
                  <input
                    type="tel"
                    value={contactPhone}
                    onChange={(e) => setContactPhone(e.target.value)}
                    disabled={!isOwnerOrAdmin}
                    placeholder="+49 711 216 0"
                    className="w-full rounded-xl border border-white/10 bg-[#0A0E17] ps-9 pe-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none disabled:opacity-60"
                  />
                </div>
              </div>
            </div>

            {/* Supported Guidance Languages */}
            <div className="space-y-3 text-start pt-2">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div>
                  <label className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                    <Globe className="w-4 h-4 text-emerald-400" />
                    Supported Guidance Languages for Citizens
                  </label>
                  <p className="text-[11px] text-slate-400">
                    Citizens can choose any of these languages to guide them through your official forms with plain-language explanations.
                  </p>
                </div>
                {isOwnerOrAdmin && (
                  <button
                    type="button"
                    onClick={() => setIsLanguageModalOpen(true)}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-bold text-emerald-400 hover:bg-emerald-500/20 transition-colors self-start sm:self-auto shadow-2xs"
                  >
                    <Globe className="w-3.5 h-3.5" />
                    Languages ({supportedLanguages.length})
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
                      className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-[#0A0E17] px-3 py-1.5 text-xs font-semibold text-slate-200 shadow-2xs"
                    >
                      <span className="font-bold">{nativeName}</span>
                      {englishName && englishName !== nativeName && (
                        <span className="text-[10px] text-slate-400 font-normal">
                          ({englishName})
                        </span>
                      )}
                      <span className="font-mono text-[9px] font-bold uppercase text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded">
                        {code}
                      </span>
                      {isOwnerOrAdmin && supportedLanguages.length > 1 && (
                        <button
                          type="button"
                          onClick={() => toggleLanguage(code)}
                          title={`Remove ${nativeName}`}
                          className="ms-0.5 rounded-full p-0.5 text-slate-400 hover:bg-[#151D2E] hover:text-white transition-colors"
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
                  className="btn-primary py-2 px-5 text-xs font-bold inline-flex items-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  {savingProfile ? "Saving..." : "Save Changes"}
                </button>
              </div>
            )}
          </form>
        )}

        {/* TAB 2: Official Government Verification */}
        {activeTab === "verification" && (
          <div className="space-y-6 max-w-2xl text-start">
            <div className="p-5 rounded-2xl border border-white/10 bg-[#0A0E17] flex items-start gap-4">
              <div className="p-3 rounded-xl bg-[#0F1522] border border-white/10 shadow-xs shrink-0">
                {org.is_verified_government ? (
                  <ShieldCheck className="w-6 h-6 text-emerald-400" />
                ) : org.verification_status === "pending_review" ? (
                  <Clock className="w-6 h-6 text-amber-400" />
                ) : (
                  <AlertCircle className="w-6 h-6 text-slate-400" />
                )}
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-bold text-white">
                    {org.is_verified_government
                      ? "Verified Government Authority"
                      : org.verification_status === "pending_review"
                      ? "Verification Under Official Review"
                      : "Unverified Organization"}
                  </h4>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                      org.is_verified_government
                        ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                        : org.verification_status === "pending_review"
                        ? "bg-amber-500/10 border border-amber-500/30 text-amber-300"
                        : "bg-[#151D2E] border border-white/10 text-slate-300"
                    }`}
                  >
                    {org.verification_status}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
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
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Official Verification Application
                </h3>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-200">
                    Authority / Institution Name
                  </label>
                  <input
                    type="text"
                    value={authorityName}
                    onChange={(e) => setAuthorityName(e.target.value)}
                    required
                    className="w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3.5 py-2 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-200">
                    Official Registration / Service ID
                  </label>
                  <input
                    type="text"
                    value={registrationId}
                    onChange={(e) => setRegistrationId(e.target.value)}
                    placeholder="e.g. DE-BW-08111000 or Municipal Code"
                    required
                    className="w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3.5 py-2 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-200">
                    Official Government / Institutional Domain
                  </label>
                  <input
                    type="text"
                    value={officialDomain}
                    onChange={(e) => setOfficialDomain(e.target.value)}
                    placeholder="e.g. agency.gov or city.gov"
                    required
                    className="w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3.5 py-2 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-200">
                    Submitter Role / Title
                  </label>
                  <input
                    type="text"
                    value={contactPersonTitle}
                    onChange={(e) => setContactPersonTitle(e.target.value)}
                    placeholder="e.g. Amtsleiter / Department Head"
                    required
                    className="w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3.5 py-2 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-200">
                    Additional Notes (Optional)
                  </label>
                  <textarea
                    value={verificationNotes}
                    onChange={(e) => setVerificationNotes(e.target.value)}
                    rows={2}
                    placeholder="Provide any public register links or verification documents..."
                    className="w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3.5 py-2 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
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
                  <h3 className="text-base font-bold text-white">Workspace Staff & Roles</h3>
                  <span className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-bold text-emerald-400">
                    {members.length} {members.length === 1 ? "Member" : "Members"}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-400">
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

            <div className="overflow-x-auto border border-white/10 rounded-2xl bg-[#0A0E17] shadow-2xs">
              <table className="w-full text-xs text-start">
                <thead className="bg-[#151D2E]/80 text-slate-300 font-bold border-b border-white/10 uppercase tracking-wider text-[11px]">
                  <tr>
                    <th scope="col" className="py-3.5 px-5 text-start w-5/12">Member</th>
                    <th scope="col" className="py-3.5 px-5 text-start w-3/12">Assigned Role</th>
                    <th scope="col" className="py-3.5 px-5 text-start w-2/12">Joined Date</th>
                    {isOwnerOrAdmin && (
                      <th scope="col" className="py-3.5 px-5 text-end w-2/12">Actions</th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.08]">
                  {members.map((m) => (
                    <tr key={m.id} className="hover:bg-[#151D2E]/60 transition-colors">
                      <td className="py-4 px-5">
                        <div className="flex items-center gap-3">
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/30 font-mono text-xs font-bold text-emerald-400">
                            {m.email.charAt(0).toUpperCase()}
                          </span>
                          <div>
                            <div className="font-semibold text-slate-100">{m.email}</div>
                            {m.role === "owner" && (
                              <span className="text-[10px] font-semibold text-emerald-400">
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
                            className="bg-[#0F1522] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-200 shadow-2xs focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                          >
                            <option value="admin">Administrator</option>
                            <option value="form_editor">Form Editor</option>
                            <option value="case_manager">Case Manager</option>
                            <option value="viewer">Viewer (Read-only)</option>
                          </select>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 px-3 py-1 text-xs font-bold text-emerald-400">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                            Owner
                          </span>
                        )}
                      </td>
                      <td className="py-4 px-5 text-slate-400 font-mono text-[11px]">
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
                              className="inline-flex items-center gap-1 text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 px-2.5 py-1 rounded-lg transition-colors font-medium"
                              title="Remove member from workspace"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              <span>Remove</span>
                            </button>
                          ) : (
                            <span className="text-[11px] font-medium text-slate-500 italic">
                              Primary Owner
                            </span>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                  {members.length === 0 && !loadingMembers && (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-slate-500">
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
                <Palette className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-bold text-white">
                  System View, Colors & Component Layout
                </h3>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                Customize your organization workspace, brand colors, layout sections, and public portal appearance.
              </p>
            </div>

            {/* 1. Authority Brand Colors & Palettes */}
            <div className="rounded-2xl border border-white/10 bg-[#0A0E17] p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-white">Authority Brand Colors</h4>
                  <p className="text-xs text-slate-400">
                    Choose your main brand color or pick from preset color palettes.
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
                  className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-white font-semibold"
                >
                  <RotateCcw className="w-3 h-3" /> Reset Colors
                </button>
              </div>

              {/* Popular Swatches */}
              <div className="space-y-2">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
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
                            ? "border-emerald-500 bg-emerald-500/10 ring-2 ring-emerald-500/30 text-white shadow-xs"
                            : "border-white/10 bg-[#0F1522] hover:border-white/20 text-slate-300"
                        }`}
                      >
                        <span
                          className="w-3.5 h-3.5 rounded-full border border-white/20 shrink-0"
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
                  <label className="text-xs font-bold text-slate-200">Primary Brand Color (Buttons & Highlights)</label>
                  <div className="relative flex items-center rounded-xl border border-white/10 bg-[#0F1522] shadow-2xs focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/20 transition-all p-1.5 gap-2.5">
                    {/* Seamless Edge-to-Edge Color Swatch */}
                    <label
                      className="relative w-8 h-8 rounded-lg cursor-pointer shrink-0 overflow-hidden shadow-2xs border border-white/20 hover:scale-105 active:scale-95 transition-transform"
                      title="Click to pick a color"
                    >
                      <input
                        type="color"
                        value={themeConfig.primary_color || "#10B981"}
                        onChange={(e) =>
                          setThemeConfig((prev) => ({ ...prev, primary_color: e.target.value }))
                        }
                        className="absolute -top-4 -left-4 w-20 h-20 cursor-pointer opacity-0"
                      />
                      <div
                        className="w-full h-full transition-colors"
                        style={{ backgroundColor: themeConfig.primary_color || "#10B981" }}
                      />
                    </label>

                    <div className="flex items-center flex-1 pe-2">
                      <span className="text-slate-500 font-mono text-xs select-none">#</span>
                      <input
                        type="text"
                        value={(themeConfig.primary_color || "10B981").replace(/^#/, "")}
                        onChange={(e) => {
                          const raw = e.target.value.replace(/[^0-9A-Fa-f]/g, "").slice(0, 6);
                          setThemeConfig((prev) => ({ ...prev, primary_color: `#${raw}` }));
                        }}
                        placeholder="10B981"
                        className="w-full font-mono text-xs uppercase text-white bg-transparent focus:outline-none ps-1 tracking-wider"
                      />
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-200">Accent / Secondary Color</label>
                  <div className="relative flex items-center rounded-xl border border-white/10 bg-[#0F1522] shadow-2xs focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/20 transition-all p-1.5 gap-2.5">
                    {/* Seamless Edge-to-Edge Color Swatch */}
                    <label
                      className="relative w-8 h-8 rounded-lg cursor-pointer shrink-0 overflow-hidden shadow-2xs border border-white/20 hover:scale-105 active:scale-95 transition-transform"
                      title="Click to pick a color"
                    >
                      <input
                        type="color"
                        value={themeConfig.accent_color || "#34D399"}
                        onChange={(e) =>
                          setThemeConfig((prev) => ({ ...prev, accent_color: e.target.value }))
                        }
                        className="absolute -top-4 -left-4 w-20 h-20 cursor-pointer opacity-0"
                      />
                      <div
                        className="w-full h-full transition-colors"
                        style={{ backgroundColor: themeConfig.accent_color || "#34D399" }}
                      />
                    </label>

                    <div className="flex items-center flex-1 pe-2">
                      <span className="text-slate-500 font-mono text-xs select-none">#</span>
                      <input
                        type="text"
                        value={(themeConfig.accent_color || "34D399").replace(/^#/, "")}
                        onChange={(e) => {
                          const raw = e.target.value.replace(/[^0-9A-Fa-f]/g, "").slice(0, 6);
                          setThemeConfig((prev) => ({ ...prev, accent_color: `#${raw}` }));
                        }}
                        placeholder="34D399"
                        className="w-full font-mono text-xs uppercase text-white bg-transparent focus:outline-none ps-1 tracking-wider"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 2. Sidebar & Navigation Appearance */}
            <div className="rounded-2xl border border-white/10 bg-[#0A0E17] p-6 space-y-4">
              <div>
                <h4 className="text-sm font-bold text-white">Sidebar Theme</h4>
                <p className="text-xs text-slate-400">
                  Select the visual appearance of the left administrative navigation menu.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  {
                    id: "dark" as SidebarTheme,
                    title: "Dark Authority",
                    desc: "Modern contrast dark slate background",
                    previewBg: "bg-[#0B0F19] border border-white/10",
                    previewText: "text-white",
                  },
                  {
                    id: "light" as SidebarTheme,
                    title: "Municipal Light",
                    desc: "Classic clean white government style",
                    previewBg: "bg-slate-100 border border-slate-300",
                    previewText: "text-slate-950",
                  },
                  {
                    id: "heraldic" as SidebarTheme,
                    title: "Brand Color Tint",
                    desc: "Dark sidebar tinted with your brand color",
                    previewBg: "bg-[#0b1329] border border-white/10",
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
                          ? "border-emerald-500 ring-2 ring-emerald-500/30 bg-emerald-500/10"
                          : "border-white/10 hover:border-white/20 bg-[#0F1522]"
                      }`}
                    >
                      <div
                        data-theme-locked={st.id !== "light" ? "dark" : undefined}
                        className={`h-8 w-full rounded-lg mb-2.5 flex items-center px-2.5 gap-1.5 ${st.previewBg}`}
                      >
                        <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                        <span className={`text-[10px] font-bold ${st.previewText}`}>STUTTGART</span>
                      </div>
                      <div className="text-xs font-bold text-white">{st.title}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{st.desc}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 3. Component Ordering on Dashboard */}
            <div className="rounded-2xl border border-white/10 bg-[#0A0E17] p-6 space-y-4">
              <div>
                <h4 className="text-sm font-bold text-white">Dashboard Component Ordering</h4>
                <p className="text-xs text-slate-400">
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
                      name: "Action Bar & Form Upload",
                      desc: "Upload PDF button and Public Portal link",
                    },
                    forms: {
                      name: "Official Forms & Review Studio Catalog",
                      desc: "Full table of administrative templates with search, filters, and actions",
                    },
                  };

                  return (
                    <div
                      key={sec}
                      className="flex items-center justify-between p-3.5 rounded-xl border border-white/10 bg-[#0F1522]"
                    >
                      <div className="flex items-center gap-3">
                        <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-[#151D2E] border border-white/10 text-xs font-mono font-bold text-emerald-400">
                          {idx + 1}
                        </span>
                        <div>
                          <div className="text-xs font-bold text-slate-100">{labelMap[sec]?.name}</div>
                          <div className="text-[11px] text-slate-400">{labelMap[sec]?.desc}</div>
                        </div>
                      </div>

                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => moveSection(idx, "up")}
                          disabled={idx === 0}
                          className="p-1 rounded-lg border border-white/10 bg-[#151D2E] text-slate-300 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                          title="Move up"
                        >
                          <ArrowUp className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => moveSection(idx, "down")}
                          disabled={idx === arr.length - 1}
                          className="p-1 rounded-lg border border-white/10 bg-[#151D2E] text-slate-300 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
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
            <div className="rounded-2xl border border-white/10 bg-[#0A0E17] p-6 space-y-4">
              <div>
                <h4 className="text-sm font-bold text-white">Component Visibility</h4>
                <p className="text-xs text-slate-400">
                  Toggle which elements are visible to your caseworkers and administrators.
                </p>
              </div>

              <div className="divide-y divide-white/[0.08]">
                <div className="flex items-center justify-between py-3">
                  <div>
                    <div className="text-xs font-bold text-slate-100">Show Real-Time Metrics Strip</div>
                    <div className="text-[11px] text-slate-400">
                      Display total forms, published forms, and review count cards on dashboard.
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={themeConfig.show_metrics_strip !== false}
                    onChange={(e) =>
                      setThemeConfig((prev) => ({ ...prev, show_metrics_strip: e.target.checked }))
                    }
                    className="h-4 w-4 rounded border-white/20 bg-[#0F1522] text-emerald-500 accent-emerald-500 focus:ring-emerald-500/30"
                  />
                </div>

                <div className="flex items-center justify-between py-3">
                  <div>
                    <div className="text-xs font-bold text-slate-100">Show Authority Contact & Location Details</div>
                    <div className="text-[11px] text-slate-400">
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
                    className="h-4 w-4 rounded border-white/20 bg-[#0F1522] text-emerald-500 accent-emerald-500 focus:ring-emerald-500/30"
                  />
                </div>

                <div className="flex items-center justify-between py-3">
                  <div>
                    <div className="text-xs font-bold text-slate-100">Show Public Citizen Portal Link</div>
                    <div className="text-[11px] text-slate-400">
                      Display the quick 1-click button to view public citizen intake.
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={themeConfig.show_portal_link !== false}
                    onChange={(e) =>
                      setThemeConfig((prev) => ({ ...prev, show_portal_link: e.target.checked }))
                    }
                    className="h-4 w-4 rounded border-white/20 bg-[#0F1522] text-emerald-500 accent-emerald-500 focus:ring-emerald-500/30"
                  />
                </div>
              </div>
            </div>

            {/* 5. Density & Spacing */}
            <div className="rounded-2xl border border-white/10 bg-[#0A0E17] p-6 space-y-4">
              <div>
                <h4 className="text-sm font-bold text-white">Layout Density</h4>
                <p className="text-xs text-slate-400">
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
                          ? "border-emerald-500 ring-2 ring-emerald-500/30 bg-emerald-500/10 font-bold"
                          : "border-white/10 hover:border-white/20 bg-[#0F1522]"
                      }`}
                    >
                      <div className="text-xs text-white">{d.title}</div>
                      <div className="text-[11px] text-slate-400 font-normal mt-0.5">{d.desc}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 6. Public Citizen Portal Customization */}
            <div className="rounded-2xl border border-white/10 bg-[#0A0E17] p-6 space-y-4">
              <div>
                <h4 className="text-sm font-bold text-white">Public Citizen Guidance & Notices</h4>
                <p className="text-xs text-slate-400">
                  Customize the headline and banner shown to applicants on your public portal (`/organizations/{org.slug}`).
                </p>
              </div>

              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-200">Citizen Welcome Headline</label>
                  <input
                    type="text"
                    value={themeConfig.citizen_welcome_heading || ""}
                    onChange={(e) =>
                      setThemeConfig((prev) => ({
                        ...prev,
                        citizen_welcome_heading: e.target.value,
                      }))
                    }
                    placeholder="Welcome to City Administration & Public Services"
                    className="w-full rounded-xl border border-white/10 px-3.5 py-2 text-xs bg-[#0F1522] text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-200">Public Notice Banner (Optional alert box)</label>
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
                    className="w-full rounded-xl border border-white/10 px-3.5 py-2 text-xs bg-[#0F1522] text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
                  />
                </div>
              </div>
            </div>

            {/* Live Interactive Preview Box */}
            <div className="rounded-2xl border border-white/10 bg-[#0A0E17] p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-bold text-white">Live Appearance Preview</span>
                  <span className="hidden sm:inline text-[11px] text-slate-400 font-normal">
                    — Updates automatically as you adjust colors, sidebar, and layout
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/30">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    LIVE PREVIEW
                  </span>
                </div>
              </div>

              {/* Realistic Desktop App / Browser Frame */}
              <div className="rounded-xl border border-white/10 bg-[#0F1522] shadow-md overflow-hidden text-start">
                {/* Window Chrome Header */}
                <div className="h-8 bg-[#151D2E] border-b border-white/10 px-3 flex items-center justify-between select-none">
                  <div className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-rose-400" />
                    <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                    <div className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                  </div>
                  <div className="flex items-center gap-1.5 px-3 py-0.5 rounded-md bg-[#0A0E17] border border-white/10 text-[10px] text-slate-300 font-mono shadow-2xs">
                    <Lock className="w-2.5 h-2.5 text-slate-400" />
                    <span>amt.formflow.de/portal/{org.slug}</span>
                  </div>
                  <div className="text-[10px] font-semibold text-slate-400">
                    {themeConfig.layout_density === "compact" ? "Compact" : "Comfortable"}
                  </div>
                </div>

                {/* Application Workspace inside Window */}
                <div className="flex min-h-[350px]">
                  {/* Miniature Sidebar */}
                  <div
                    data-theme-locked={themeConfig.sidebar_theme !== "light" ? "dark" : undefined}
                    className="w-44 shrink-0 p-3 flex flex-col justify-between border-r transition-colors"
                    style={{
                      backgroundColor:
                        themeConfig.sidebar_theme === "dark"
                          ? "#0B0F19"
                          : themeConfig.sidebar_theme === "heraldic"
                          ? "#0b1329"
                          : "#FFFFFF",
                      backgroundImage:
                        themeConfig.sidebar_theme === "heraldic"
                          ? `linear-gradient(180deg, ${themeConfig.primary_color || "#10B981"}26 0%, transparent 100%)`
                          : undefined,
                      borderColor:
                        themeConfig.sidebar_theme === "dark"
                          ? "#1E293B"
                          : themeConfig.sidebar_theme === "heraldic"
                          ? (themeConfig.primary_color || "#10B981") + "30"
                          : "#E2E8F0",
                      color:
                        themeConfig.sidebar_theme === "light"
                          ? "#0F172A"
                          : "#F8FAFC",
                    }}
                  >
                    <div className="space-y-4">
                      {/* Logo & Org Name */}
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-7 h-7 rounded-lg border shadow-2xs flex items-center justify-center shrink-0 overflow-hidden ${
                            org.logo_storage_path
                              ? "bg-white p-1 border-white/20"
                              : "bg-[#151D2E] p-0.5 border-white/10"
                          }`}
                        >
                          {org.logo_storage_path ? (
                            /* eslint-disable-next-line @next/next/no-img-element */
                            <img
                              src={`/api/organizations/${org.id}/logo?v=${logoVersion}`}
                              alt="Emblem"
                              className="w-full h-full object-contain"
                            />
                          ) : (
                            <Building2 className="w-3.5 h-3.5 text-slate-400" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <div className="text-[11px] font-bold truncate leading-tight">
                            {org.name.split("—")[0].trim()}
                          </div>
                          <div className="text-[9px] opacity-60 leading-tight">Organization Portal</div>
                        </div>
                      </div>

                      {/* Mini Nav Links */}
                      <div className="space-y-1">
                        <div
                          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[10px] font-bold shadow-2xs cursor-default"
                          style={{
                            backgroundColor: themeConfig.primary_color || "#10B981",
                            color: getContrastTextColor(themeConfig.primary_color || "#10B981"),
                          }}
                        >
                          <FileText className="w-3 h-3" />
                          <span>Workspace & Forms</span>
                        </div>
                        <div
                          className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[10px] font-medium opacity-70 ${
                            themeConfig.sidebar_theme === "light" ? "hover:bg-slate-100" : "hover:bg-white/5"
                          }`}
                        >
                          <Users className="w-3 h-3" />
                          <span>Cases & Intake</span>
                        </div>
                        <div
                          className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[10px] font-medium opacity-70 ${
                            themeConfig.sidebar_theme === "light" ? "hover:bg-slate-100" : "hover:bg-white/5"
                          }`}
                        >
                          <Globe className="w-3 h-3" />
                          <span>Public Portal</span>
                        </div>
                        <div
                          className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[10px] font-medium opacity-70 ${
                            themeConfig.sidebar_theme === "light" ? "hover:bg-slate-100" : "hover:bg-white/5"
                          }`}
                        >
                          <Sliders className="w-3 h-3" />
                          <span>Settings</span>
                        </div>
                      </div>
                    </div>

                    {/* User Mini Profile */}
                    <div
                      className={`pt-3 border-t flex items-center gap-2 ${
                        themeConfig.sidebar_theme === "light" ? "border-slate-200" : "border-white/10"
                      }`}
                    >
                      <div
                        className={`w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold ${
                          themeConfig.sidebar_theme === "light"
                            ? "bg-slate-200 text-slate-700"
                            : "bg-white/15 text-slate-200"
                        }`}
                      >
                        A
                      </div>
                      <div className="min-w-0 text-[9px] opacity-75 truncate">
                        Case Officer (Admin)
                      </div>
                    </div>
                  </div>

                  {/* Miniature Workspace Content Canvas */}
                  <div className="flex-1 bg-[#0A0E17] p-4 space-y-3 overflow-hidden">
                    {/* Notice Banner */}
                    {themeConfig.citizen_notice_banner && (
                      <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-[10px] text-amber-200 flex items-center gap-2 shadow-2xs">
                        <AlertCircle className="w-3 h-3 shrink-0 text-amber-400" />
                        <span className="font-medium truncate">{themeConfig.citizen_notice_banner}</span>
                      </div>
                    )}

                    {/* Section Ordering Dynamic Renderer */}
                    {(themeConfig.section_order || ["header", "metrics", "actions", "forms"]).map((sec) => {
                      if (sec === "header") {
                        return (
                          <div
                            key="header"
                            className="bg-[#0F1522] rounded-xl border border-white/10 p-3 shadow-2xs flex items-center justify-between gap-3"
                          >
                            <div className="flex items-center gap-2.5 min-w-0">
                              <div
                                className={`w-8 h-8 rounded-lg border shrink-0 flex items-center justify-center overflow-hidden ${
                                  org.logo_storage_path
                                    ? "bg-white p-1 border-white/20"
                                    : "bg-[#151D2E] p-1 border-white/10"
                                }`}
                              >
                                {org.logo_storage_path ? (
                                  /* eslint-disable-next-line @next/next/no-img-element */
                                  <img
                                    src={`/api/organizations/${org.id}/logo?v=${logoVersion}`}
                                    alt="Logo"
                                    className="w-full h-full object-contain"
                                  />
                                ) : (
                                  <Building2 className="w-4 h-4 text-slate-400" />
                                )}
                              </div>
                              <div className="min-w-0">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <div className="text-xs font-bold text-white truncate">{org.name}</div>
                                  <span className="inline-flex items-center gap-0.5 rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-400 border border-emerald-500/30">
                                    <ShieldCheck className="w-2.5 h-2.5 text-emerald-400" />
                                    Verified
                                  </span>
                                </div>
                                {themeConfig.show_authority_metadata !== false && (
                                  <div className="text-[10px] text-slate-400 flex items-center gap-2 mt-0.5">
                                    <span className="flex items-center gap-0.5">
                                      <MapPin className="w-2.5 h-2.5" /> City Hall, Public Services
                                    </span>
                                    <span className="flex items-center gap-0.5">
                                      <Globe className="w-2.5 h-2.5" /> agency.gov
                                    </span>
                                  </div>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-1.5 shrink-0">
                              {themeConfig.show_portal_link !== false && (
                                <div className="px-2 py-1 rounded-lg border border-white/10 bg-[#151D2E] text-[10px] font-semibold text-slate-200 shadow-2xs flex items-center gap-1">
                                  <Globe className="w-2.5 h-2.5 text-slate-400" />
                                  <span>Portal</span>
                                  <ExternalLink className="w-2 h-2 text-slate-500" />
                                </div>
                              )}
                              <div
                                className="px-2.5 py-1 rounded-lg text-[10px] font-bold shadow-2xs flex items-center gap-1 cursor-default"
                                style={{
                                  backgroundColor: themeConfig.primary_color || "#10B981",
                                  color: getContrastTextColor(themeConfig.primary_color || "#10B981"),
                                }}
                              >
                                <Upload className="w-2.5 h-2.5" />
                                <span>Upload PDF</span>
                              </div>
                            </div>
                          </div>
                        );
                      }

                      if (sec === "metrics" && themeConfig.show_metrics_strip !== false) {
                        return (
                          <div key="metrics" className="grid grid-cols-4 gap-2">
                            {[
                              { label: "Total Forms", val: "12", color: themeConfig.primary_color || "#10B981" },
                              { label: "Live in Portal", val: "8", color: "#10B981" },
                              { label: "Needs Review", val: "2", color: "#F59E0B" },
                              { label: "Archived", val: "2", color: "#64748B" },
                            ].map((m, i) => (
                              <div
                                key={i}
                                className="p-2 rounded-xl bg-[#0F1522] border border-white/10 shadow-2xs text-start relative overflow-hidden"
                              >
                                <div
                                  className="absolute top-0 left-0 right-0 h-0.5"
                                  style={{ backgroundColor: m.color }}
                                />
                                <div className="text-[9px] font-medium text-slate-400">{m.label}</div>
                                <div className="text-sm font-bold text-white mt-0.5">{m.val}</div>
                              </div>
                            ))}
                          </div>
                        );
                      }

                      if (sec === "actions") {
                        return (
                          <div key="actions" className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#0F1522] border border-white/10 text-[10px] text-slate-400 w-44 shadow-2xs">
                              <Search className="w-3 h-3 text-slate-500" />
                              <span>Search forms...</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <span
                                className="px-2 py-0.5 rounded-md text-[9px] font-bold shadow-2xs"
                                style={{
                                  backgroundColor: themeConfig.primary_color || "#10B981",
                                  color: getContrastTextColor(themeConfig.primary_color || "#10B981"),
                                }}
                              >
                                All (12)
                              </span>
                              <span className="px-2 py-0.5 rounded-md text-[9px] font-medium text-slate-300 bg-[#0F1522] border border-white/10">
                                Live
                              </span>
                              <span className="px-2 py-0.5 rounded-md text-[9px] font-medium text-slate-300 bg-[#0F1522] border border-white/10">
                                Review
                              </span>
                            </div>
                          </div>
                        );
                      }

                      if (sec === "forms") {
                        return (
                          <div
                            key="forms"
                            className="bg-[#0F1522] rounded-xl border border-white/10 shadow-2xs overflow-hidden"
                          >
                            <div className="px-3 py-1.5 bg-[#151D2E] border-b border-white/10 flex items-center justify-between text-[9px] font-bold text-slate-400 uppercase tracking-wider">
                              <span>Official Form Template</span>
                              <span>Status & Fields</span>
                            </div>
                            <div className="divide-y divide-white/[0.08] text-[10px]">
                              <div className="px-3 py-1.5 flex items-center justify-between hover:bg-[#151D2E]/60">
                                <div>
                                  <div className="font-semibold text-slate-100">
                                    Landlord Housing Confirmation Form
                                  </div>
                                  <div className="text-[9px] text-slate-400">Civil Registry • Ready to Fill</div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-[9px] text-slate-400">8 Fields</span>
                                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                                    Live
                                  </span>
                                </div>
                              </div>

                              <div className="px-3 py-1.5 flex items-center justify-between hover:bg-[#151D2E]/60">
                                <div>
                                  <div className="font-semibold text-slate-100">
                                    Residence & Work Permit Application
                                  </div>
                                  <div className="text-[9px] text-slate-400">Immigration Services • Fast-track</div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-[9px] text-slate-400">14 Fields</span>
                                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30">
                                    Review
                                  </span>
                                </div>
                              </div>

                              <div className="px-3 py-1.5 flex items-center justify-between hover:bg-[#151D2E]/60">
                                <div>
                                  <div className="font-semibold text-slate-100">
                                    Commercial Business Registration
                                  </div>
                                  <div className="text-[9px] text-slate-400">Economic Affairs • Verified</div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-[9px] text-slate-400">11 Fields</span>
                                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                                    Live
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      }

                      return null;
                    })}
                  </div>
                </div>
              </div>
            </div>

            {/* Save Button */}
            {isOwnerOrAdmin && (
              <div className="pt-2 flex justify-end">
                <button
                  type="submit"
                  disabled={savingTheme}
                  style={{
                    backgroundColor: themeConfig.primary_color || "#10b981",
                    color: getContrastTextColor(themeConfig.primary_color || "#10b981"),
                  }}
                  className="px-5 py-2 rounded-xl text-xs font-bold shadow-sm inline-flex items-center gap-2 hover:opacity-90 active:scale-[0.98] transition-all cursor-pointer"
                >
                  <Save className="w-4 h-4" />
                  <span>{savingTheme ? "Saving..." : "Save Changes"}</span>
                </button>
              </div>
            )}
          </form>
        )}

        {/* TAB 5: Categories & Taxonomy */}
        {activeTab === "categories" && (
          <OrganizationCategoryManager supportedLanguages={supportedLanguages} />
        )}
      </div>

      {/* Invite Member Modal */}
      {isInviteModalOpen && (
        <div className="fixed inset-0 z-50 bg-[#060910]/80 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#0F1522] rounded-2xl border border-white/10 text-slate-100 max-w-md w-full p-6 shadow-xl space-y-4 text-start">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">Invite Team Member</h3>
              <button
                onClick={() => setIsInviteModalOpen(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleInviteMember} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-200">Colleague Email</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@amt.de"
                  required
                  className="w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-200">Role & Permissions</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="w-full rounded-xl border border-white/10 px-3.5 py-2.5 text-xs bg-[#0A0E17] text-slate-100 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 focus:outline-none"
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
