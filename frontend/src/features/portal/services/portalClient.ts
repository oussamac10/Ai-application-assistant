import { getCsrfToken } from "@/features/auth/services/csrf";
import {
  CandidateIntakeInfo,
  Case,
  CaseCreatePayload,
  CaseUpdatePayload,
  Organization,
  OrganizationMember,
  OrganizationProfileUpdatePayload,
  OrganizationVerificationPayload,
} from "../types";

export async function getCurrentOrganization(): Promise<Organization> {
  const res = await fetch("/api/organizations/current", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch organization workspace.");
  }
  return res.json();
}

export async function updateOrganizationProfile(
  payload: OrganizationProfileUpdatePayload
): Promise<Organization> {
  const csrf = getCsrfToken();
  const res = await fetch("/api/organizations/current", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "x-csrf-token": csrf } : {}),
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update organization profile.");
  }
  return res.json();
}

export async function submitOrganizationVerification(
  payload: OrganizationVerificationPayload
): Promise<Organization> {
  const csrf = getCsrfToken();
  const res = await fetch("/api/organizations/current/verification", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "x-csrf-token": csrf } : {}),
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to submit verification request.");
  }
  return res.json();
}

export async function uploadOrganizationLogo(file: File): Promise<Organization> {
  const csrf = getCsrfToken();
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/api/organizations/current/logo", {
    method: "POST",
    headers: {
      ...(csrf ? { "x-csrf-token": csrf } : {}),
    },
    credentials: "include",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to upload organization logo.");
  }
  return res.json();
}

export async function listOrganizationMembers(): Promise<OrganizationMember[]> {
  const res = await fetch("/api/organizations/current/members", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to list organization members.");
  }
  return res.json();
}

export async function inviteOrganizationMember(
  email: string,
  role: string
): Promise<OrganizationMember> {
  const csrf = getCsrfToken();
  const res = await fetch("/api/organizations/current/members", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "x-csrf-token": csrf } : {}),
    },
    credentials: "include",
    body: JSON.stringify({ email, role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to invite organization member.");
  }
  return res.json();
}

export async function updateMemberRole(
  userId: string,
  role: string
): Promise<OrganizationMember> {
  const csrf = getCsrfToken();
  const res = await fetch(`/api/organizations/current/members/${userId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "x-csrf-token": csrf } : {}),
    },
    credentials: "include",
    body: JSON.stringify({ role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update member role.");
  }
  return res.json();
}

export async function removeMember(userId: string): Promise<void> {
  const csrf = getCsrfToken();
  const res = await fetch(`/api/organizations/current/members/${userId}`, {
    method: "DELETE",
    headers: {
      ...(csrf ? { "x-csrf-token": csrf } : {}),
    },
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to remove member.");
  }
}

export async function listCases(): Promise<Case[]> {
  const res = await fetch("/api/cases", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to list candidate cases.");
  }
  return res.json();
}

export async function createCase(payload: CaseCreatePayload): Promise<Case> {
  const csrf = getCsrfToken();
  const res = await fetch("/api/cases", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "x-csrf-token": csrf } : {}),
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create candidate case.");
  }
  return res.json();
}

export async function getCase(publicId: string): Promise<Case> {
  const res = await fetch(`/api/cases/${publicId}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch case details.");
  }
  return res.json();
}

export async function updateCase(
  publicId: string,
  payload: CaseUpdatePayload
): Promise<Case> {
  const csrf = getCsrfToken();
  const res = await fetch(`/api/cases/${publicId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "x-csrf-token": csrf } : {}),
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update case.");
  }
  return res.json();
}

export async function redeemCandidateInvite(
  token: string
): Promise<CandidateIntakeInfo> {
  const res = await fetch(`/api/cases/invite/${encodeURIComponent(token)}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Invalid or expired candidate invite link.");
  }
  return res.json();
}

export async function getSubscription(): Promise<import("../types").SubscriptionInfo> {
  const res = await fetch("/api/billing/subscription", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch subscription status.");
  }
  return res.json();
}

export async function getPlans(): Promise<import("../types").PlanInfo[]> {
  const res = await fetch("/api/billing/plans", {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to fetch plans.");
  }
  return res.json();
}

export async function createCheckoutSession(
  organizationId: string,
  planKey: string
): Promise<{ checkout_url: string; session_id: string }> {
  const csrf = getCsrfToken();
  const res = await fetch("/api/billing/checkout", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "x-csrf-token": csrf } : {}),
    },
    credentials: "include",
    body: JSON.stringify({
      organization_id: organizationId,
      plan_key: planKey,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to initiate checkout session.");
  }
  return res.json();
}

export async function createPortalSession(
  organizationId: string
): Promise<{ portal_url: string }> {
  const csrf = getCsrfToken();
  const res = await fetch("/api/billing/portal", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "x-csrf-token": csrf } : {}),
    },
    credentials: "include",
    body: JSON.stringify({
      organization_id: organizationId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to open billing portal.");
  }
  return res.json();
}
